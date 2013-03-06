'''
TODO

Created on 31/3/13
@author: Ben Davies
'''

from itertools import product
from numpy import sum, isnan, reshape, zeros, float32, vstack, squeeze
from scipy.linalg import lstsq
from numpy.linalg import pinv

import algorithm
from mst import default_mst

# Orbital correction
# 0) Config file stuff:
#		Add the orbital params
#		orbfit = 0: off, 1=do it
#		orbfitmethod: 1 or 2 (see conf file) (AKA independent and networked methods)
#		orbrefest = orb_ref_est, 0=off, 1=on (IGNORE for the time being - something
#               to do with removing the constant param 'c' from y = mx+c)
#		orbmaskflag = IGNORE for now. Used to mask out some patches, eg. if there is
#                 an earthquake signal somewhere.
#
# 1) resample/multilook the data to have less pixels (for comp efficiency)
# optional? VU can handle larger arrays (new sys=?)
#
# 2) design matrix (orbdesign.m)
#
# 3) linear regression/inversion - get params (ala orbcorrect.m)
#
# 4) forward calculation (orbfwd.m)
#		create 2D orbital correctionl layer from the model params


# constants
INDEPENDENT_METHOD = 1
NETWORK_METHOD = 2

PLANAR = 1
QUADRATIC = 2


def orbital_correction(ifgs, degree, method, offset=True):
	'''Top level method for correcting orbital error TODO
	ifgs - list of Ifg objs to correct
	degree - PLANAR or QUADRATIC
	method - INDEPENDENT_METHOD or NETWORK_METHOD
	offset = True/False TODO
	'''

	# TODO: save corrected layers to new file or use intermediate arrays?
	# TODO: offsets

	if degree not in [PLANAR, QUADRATIC]:
		msg = "Invalid degree of %s for orbital correction" % degree
		raise OrbitalCorrectionError(msg)

	if method == NETWORK_METHOD:
		# Cut down to the smallest tree with all nodes
		# TODO: do this as a filter step outside the main func? More MODULAR
		#mst = default_mst(ifgs)
		#from algorithm import ifg_date_lookup
		#sub_ifgs = [ifg_date_lookup(ifgs, mas_slv) for mas_slv in mst.iteritems()]
		#1/0

		# TODO: reverse lookup to map edges -> ifgs
		#return _get_net_correction(sub_ifgs, degree, offset)
		return _get_net_correction(ifgs, degree, offset)

	elif method == INDEPENDENT_METHOD:
		# FIXME: determine how to work this into the ifgs. Generate new Ifgs? Update
		# the old ifgs and flag the corrections in metadata?
		return [_get_ind_correction(i, degree, offset) for i in ifgs]
	else:
		msg = "Unknown method '%s'" % method
		raise OrbitalCorrectionError(msg)


def _get_ind_correction(ifg, degree, offset):
	'''Calculates and returns orbital correction array for an ifg'''

	vphase = reshape(ifg.phase_data, ifg.num_cells) # vectorised, contains NODATA
	dm = get_design_matrix(ifg, degree, offset)
	assert len(vphase) == len(dm)

	# filter NaNs out before getting model
	tmp = dm[~isnan(vphase)]
	fd = vphase[~isnan(vphase)]
	model, _, rank, _ = lstsq(tmp, fd)
	exp_len = 2 if degree == PLANAR else 5
	if offset:
		exp_len += 1
	assert len(model) == exp_len

	# calculate forward model & morph back to 2D
	tmp = sum(dm * model, axis=1) # d = ax + by
	correction = reshape(tmp, ifg.phase_data.shape)
	return correction


def _get_net_correction(ifgs, degree, offset):
	'''Returns the TODO
	ifgs - assumed to be Ifgs from a prior MST step
	degree - PLANAR or QUADRATIC
	offset - True/False for including TODO
	'''
	# TODO: multilooking (do seperately/prior to this as a batch job?)

	# get DM / clear out the NaNs based on obs
	tmp = vstack([i.phase_data.reshape((i.num_cells, 1)) for i in ifgs])
	vphase = squeeze(tmp)
	dm = get_network_design_matrix(ifgs, degree, offset)
	assert len(vphase) == len(dm)

	# filter NaNs out before getting model
	tmp = dm[~isnan(vphase)]
	fd = vphase[~isnan(vphase)]
	model = pinv(tmp, 1e-6) * fd
	return model


def get_design_matrix(ifg, degree, offset):
	'''Returns design matrix with 2 columns for linear model parameters'''

	nparams = 2 if degree == PLANAR else 5
	if offset:
		nparams += 1  # eg. y = mx + offset

	# init design matrix
	shape = (ifg.num_cells, nparams)
	data = zeros(shape, dtype=float32)
	rows = iter(data)

	dmfun = _planar_dm if degree == PLANAR else _quadratic_dm
	dmfun(ifg, rows, offset)
	return data


# TODO: can this be refactored under one get_design_matrix() func?
def get_network_design_matrix(ifgs, degree, offset):
	'''Returns a larger format design matrix for networked error correction.'''

	if degree not in [PLANAR, QUADRATIC]:
		raise OrbitalCorrectionError("Invalid degree argument")

	num_ifgs = len(ifgs)
	if num_ifgs < 2:
		raise OrbitalCorrectionError("Invalid number of Ifgs")

	# TODO: refactor to prevent duplication with get_design_matrix()?
	nparams = 2 if degree == PLANAR else 5
	if offset:
		nparams += 1  # eg. b/offset in (y = mx + b) is an extra param

	# sort out master and slave date IDs
	dates = [ifg.MASTER for ifg in ifgs] + [ifg.SLAVE for ifg in ifgs]
	ids = algorithm.master_slave_ids(dates)
	num_epochs = max(ids.values()) + 1 # convert from zero indexed ID

	# init design matrix
	shape = (ifgs[0].num_cells * num_ifgs, nparams * num_epochs)
	data = zeros(shape, dtype=float32)

	# paste in individual design matrices
	for i, ifg in enumerate(ifgs):
		tmp = get_design_matrix(ifg, degree, offset)
		rs = i * ifg.num_cells
		rf = rs + ifg.num_cells

		# generate column indices into data based on master position
		mascs = ids[ifg.MASTER] * nparams
		mascf = mascs + nparams
		data[rs:rf, mascs:mascf] = -tmp

		# then for slave
		slvcs =	ids[ifg.SLAVE] * nparams
		slvcf = slvcs + nparams
		data[rs:rf, slvcs:slvcf] = tmp

	return data


def _planar_dm(ifg, rows, offset):
	# apply positional parameter values, multiply pixel coordinate by cell size to
	# get distance (a coord by itself doesn't tell us distance from origin)

	# TODO: optimise with meshgrid calls?
	# TODO: make more efficient by pre generating xranges and doing array ops?
	# TODO: coordinates generator for Ifgs?

	if offset:
		for y,x in product(xrange(ifg.FILE_LENGTH), xrange(ifg.WIDTH)):
			row = rows.next() # TODO: make faster with vstack?
			row[:] = [x * ifg.X_STEP, y * ifg.Y_STEP, 1] # FIXME: change to (Y|X)SIZE
	else:
		for y,x in product(xrange(ifg.FILE_LENGTH), xrange(ifg.WIDTH)):
			row = rows.next() # TODO: make faster with vstack?
			row[:] = [x * ifg.X_STEP, y * ifg.Y_STEP] # FIXME: change to (Y|X)SIZE, needs proj4


def _quadratic_dm(ifg, rows, offset):
	# apply positional parameter values, multiply pixel coordinate by cell size to
	# get distance (a coord by itself doesn't tell us distance from origin)
	yst, xst = ifg.Y_STEP, ifg.X_STEP # FIXME: sizes

	if offset:
		for y,x in product(xrange(ifg.FILE_LENGTH), xrange(ifg.WIDTH)):
			row = rows.next()
			y2 = y * yst
			x2 = x * xst
			row[:] = [x2**2, y2**2, x2*y2, x2, y2, 1] # FIXME: change to (Y|X)SIZE
	else:
		for y,x in product(xrange(ifg.FILE_LENGTH), xrange(ifg.WIDTH)):
			row = rows.next()
			y2 = y * yst
			x2 = x * xst
			row[:] = [x2**2, y2**2, x2*y2, x2, y2] # FIXME: change to (Y|X)SIZE, needs proj4



class OrbitalCorrectionError(Exception):
	pass
