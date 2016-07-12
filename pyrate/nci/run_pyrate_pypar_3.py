import os
import sys
import numpy as np
from collections import namedtuple
from osgeo import gdal

from pyrate import config as cf
from pyrate import ifgconstants as ifc
from pyrate import linrate
from pyrate import shared
from pyrate import timeseries
from pyrate.nci.parallel import Parallel
from pyrate.scripts import run_pyrate
from pyrate.scripts.run_pyrate import write_msg
from pyrate.shared import get_tmpdir
from pyrate.nci import common_nci
gdal.SetCacheMax(64)

TMPDIR = get_tmpdir()

__author__ = 'sudipta'

# Constants
MASTER_PROCESS = 0
data_path = 'DATAPATH'

PrereadIfg = namedtuple('PrereadIfg', 'path nan_fraction master slave time_span')


def main(params, config_file=sys.argv[1]):

    # setup paths
    xlks, ylks, crop = run_pyrate.transform_params(params)
    base_unw_paths = run_pyrate.original_ifg_paths(params[cf.IFG_FILE_LIST])
    dest_tifs = run_pyrate.get_dest_paths(base_unw_paths, crop, params, xlks)

    # Setting up parallelisation
    parallel = Parallel(True)
    rank = parallel.rank

    # calculate process information
    ifg_shape, process_tiles, process_indices, tiles = \
        common_nci.get_process_tiles(dest_tifs, parallel, params)

    output_dir = params[cf.OUT_DIR]
    preread_ifgs = os.path.join(output_dir, 'preread_ifgs.pk')

    maxvar_file = os.path.join(params[cf.OUT_DIR], 'maxvar.npy')
    vcmt_file = os.path.join(params[cf.OUT_DIR], 'vcmt.npy')

    maxvar, vcmt = np.load(maxvar_file), np.load(vcmt_file)

    parallel.barrier()

    if rank == MASTER_PROCESS:
        for d in dest_tifs:
            save_latest_phase(d, output_dir, tiles)

    # linrate mpi computation
    linrate_mpi(rank, dest_tifs, parallel, params, vcmt,
                process_tiles, process_indices, ifg_shape, preread_ifgs)
    # TODO: write linrate aggregation function from linrate tiles

    parallel.barrier()
    # time series mpi computation
    if params[cf.TIME_SERIES_CAL]:
        time_series_mpi(dest_tifs, params, vcmt, process_tiles,
                        process_indices, preread_ifgs)
        parallel.barrier()
        write_time_series_geotiff_mpi(dest_tifs, params, tiles, parallel, rank)

    parallel.finalize()


def save_latest_phase(d, output_dir, tiles):
    ifg = shared.Ifg(d)
    ifg.open()
    ifg.nodata_value = 0
    phase_data = ifg.phase_data
    for t in tiles:
        p_data = phase_data[t.top_left_y:t.bottom_right_y,
                 t.top_left_x:t.bottom_right_x]
        phase_file = 'phase_data_{}_{}.npy'.format(
            os.path.basename(d).split('.')[0], t.index)

        np.save(file=os.path.join(output_dir, phase_file),
                arr=p_data)
    return ifg


def write_time_series_geotiff_mpi(dest_tifs, params, tiles, parallel, MPI_id):
    ifgs = shared.prepare_ifgs_without_phase(dest_tifs, params)
    epochlist, gt, md, wkt = run_pyrate.setup_metadata(ifgs, params)

    # load the first tsincr file to determine the number of time series tifs
    tsincr_file = os.path.join(TMPDIR, 'tsincr_0.npy')
    tsincr = np.load(file=tsincr_file)

    no_ts_tifs = tsincr.shape[2]
    process_tifs = parallel.calc_indices(no_ts_tifs)

    # depending on nvelpar, this will not fit in memory
    # e.g. nvelpar=100, nrows=10000, ncols=10000, 32bit floats need 40GB memory
    # 32 * 100 * 10000 * 10000 / 8 bytes = 4e10 bytes = 40 GB
    # the double for loop is helps us over come the memory limit
    print 'process {} will write {} ts tifs of total {}'.format(
        MPI_id, len(process_tifs), no_ts_tifs)

    for i in process_tifs:
        tsincr_g = np.empty(shape=ifgs[0].shape, dtype=np.float32)
        tscum_g = np.empty(shape=ifgs[0].shape, dtype=np.float32)
        for n, t in enumerate(tiles):
            tsincr_file = os.path.join(TMPDIR, 'tsincr_{}.npy'.format(n))
            tscum_file = os.path.join(TMPDIR, 'tscuml_{}.npy'.format(n))
            tsincr = np.load(file=tsincr_file)
            tscum = np.load(file=tscum_file)

            md[ifc.MASTER_DATE] = epochlist.dates[i + 1]
            md['PR_SEQ_POS'] = i  # sequence position
            tsincr_g[t.top_left_y:t.bottom_right_y,
                     t.top_left_x:t.bottom_right_x] = tsincr[:, :, i]
            dest = os.path.join(params[cf.OUT_DIR],
                'tsincr' + "_" + str(epochlist.dates[i + 1]) + ".tif")
            md[ifc.PRTYPE] = 'tsincr'
            shared.write_output_geotiff(md, gt, wkt, tsincr_g, dest, np.nan)

            tscum_g[t.top_left_y:t.bottom_right_y,
                t.top_left_x:t.bottom_right_x] = tscum[:, :, i]
            dest = os.path.join(params[cf.OUT_DIR],
                'tscuml' + "_" + str(epochlist.dates[i + 1]) + ".tif")
            md[ifc.PRTYPE] = 'tscuml'
            shared.write_output_geotiff(md, gt, wkt, tscum_g, dest, np.nan)


def linrate_mpi(MPI_myID, ifg_paths, parallel, params, vcmt,
                process_tiles, process_indices, ifg_shape, preread_ifgs):
    write_msg('Calculating linear rate')
    for i, t in zip(process_indices, process_tiles):
        print 'calculating lin rate of tile {}'.format(i)
        ifg_parts = [shared.IfgPart(p, t, preread_ifgs) for p in ifg_paths]
        mst_n = os.path.join(TMPDIR, 'mst_mat_{}.npy'.format(i))
        mst_grid_n = np.load(mst_n)
        res = linrate.linear_rate(ifg_parts, params, vcmt, mst_grid_n)

        for r in res:
            if r is None:
                raise ValueError('TODO: bad value')
        rate, error, samples = res
        # declare file names
        rate_file = os.path.join(params[cf.OUT_DIR], 'rate_{}.npy'.format(i))
        error_file = os.path.join(params[cf.OUT_DIR], 'error_{}.npy'.format(i))
        samples_file = os.path.join(params[cf.OUT_DIR],
                                    'samples_{}.npy'.format(i))

        np.save(file=rate_file, arr=rate)
        np.save(file=error_file, arr=rate)
        np.save(file=samples_file, arr=samples)


def time_series_mpi(ifg_paths, params, vcmt, process_tiles, process_indices,
                    preread_ifgs):
    write_msg('Calculating time series')  # this should be logged

    for t in process_tiles:
        i = t.index
        ifg_parts = [shared.IfgPart(p, t, preread_ifgs) for p in ifg_paths]
        mst_file_process_n = os.path.join(TMPDIR, 'mst_mat_{}.npy'.format(i))
        mst_tile = np.load(mst_file_process_n)
        res = timeseries.time_series(ifg_parts, params, vcmt, mst_tile)
        tsincr, tscum, tsvel = res
        tsincr_file = os.path.join(TMPDIR, 'tsincr_{}.npy'.format(i))
        tscum_file = os.path.join(TMPDIR, 'tscuml_{}.npy'.format(i))
        np.save(file=tsincr_file, arr=tsincr)
        np.save(file=tscum_file, arr=tscum)


if __name__ == '__main__':
    # read in the config file, and params for the simulation
    params = run_pyrate.get_ifg_paths()[2]
    main(params)
