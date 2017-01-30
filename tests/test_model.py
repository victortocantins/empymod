# model. Status: 10/13
import numpy as np
from os.path import join, dirname
from numpy.testing import assert_allclose

# Import main modelling routines from empymod directly to ensure they are in
# the __init__.py-file.
from empymod import bipole, dipole, frequency, time
# Import rest from model
from empymod.model import gpr, wavenumber, fem, tem
from empymod.kernel import fullspace, halfspace

# These are kind of macro-tests, as they check the final results.
# I try to use different parameters for each test, to cover a wide range of
# possibilities. It won't be possible to check all the possibilities though.
# Add tests when issues arise!

# Load required data
# Data generated with create_empymod.py [27/01/2017]
DATAEMPYMOD = np.load(join(dirname(__file__), 'data_empymod.npz'))
# Data generated with create_fem_tem.py [27/01/2017]
DATAFEMTEM = np.load(join(dirname(__file__), 'data_fem_tem.npz'))
# Data generated with create_green3d.py [30/01/2017]
GREEN3D = np.load(join(dirname(__file__), 'data_green3d.npz'))


class TestBipole:                                                   # 1. bipole
    # => Main and most important checks/comparisons

    # test freq, time (all signals)
    # test loop-options
    # test opt-options
    # test integration points
    # test source strength
    # test ht args
    # test ft args

    def test_fullspace(self):                                   # 1.1 fullspace
        # Comparison to analytical fullspace solution
        fs = DATAEMPYMOD['fs'][()]
        fsbp = DATAEMPYMOD['fsbp'][()]
        for key in fs:
            # Get fullspace
            fs_res = fullspace(**fs[key])
            # Get bipole
            bip_res = bipole(**fsbp[key])
            # Check
            assert_allclose(fs_res, bip_res)

    def test_halfspace(self):                                   # 1.2 halfspace
        # Comparison to analytical fullspace solution
        hs = DATAEMPYMOD['hs'][()]
        hsbp = DATAEMPYMOD['hsbp'][()]
        for key in hs:
            # Get halfspace
            hs_res = halfspace(**hs[key])
            # Get bipole
            bip_res = bipole(**hsbp[key])
            # Check
            assert_allclose(hs_res, bip_res)

    # 1.3. Comparison to EMmod
    # General tests, as in Comparing.ipynb

    # 1.4. Comparison to DIPOLE1D
    # Test finite length bipoles, rotated

    def test_green3d(self):                        # 1.5. Comparison to Green3D
        # Test a few anisotropic cases
        def crec(rec, azm, dip):
            return [rec[0], rec[1], rec[2], azm, dip]

        def get_xyz(src, rec, depth, res, freq, aniso, strength, srcpts, verb):
            x = bipole(src=src, rec=crec(rec, 0, 0), depth=depth, res=res,
                       freqtime=freq, signal=None, aniso=aniso,
                       strength=strength, srcpts=srcpts, verb=verb)
            y = bipole(src=src, rec=crec(rec, 90, 0), depth=depth, res=res,
                       freqtime=freq, signal=None, aniso=aniso,
                       strength=strength, srcpts=srcpts, verb=verb)
            z = bipole(src=src, rec=crec(rec, 0, 90), depth=depth, res=res,
                       freqtime=freq, signal=None, aniso=aniso,
                       strength=strength, srcpts=srcpts, verb=verb)
            return x, y, z

        # 1. x-directed dipole
        inp, res = GREEN3D['xdirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        assert_allclose(Ex, res[0], rtol=5e-3, equal_nan=True)
        assert_allclose(Ey, res[1], rtol=5e-3, equal_nan=True)
        assert_allclose(Ez, res[2], rtol=5e-3, equal_nan=True)

        # 2. y-directed dipole
        inp, res = GREEN3D['ydirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 1e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 3. z-directed dipole
        inp, res = GREEN3D['zdirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 4. xy-directed dipole
        inp, res = GREEN3D['xydirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 1e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 5. xz-directed dipole
        inp, res = GREEN3D['xzdirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 6. yz-directed dipole
        inp, res = GREEN3D['yzdirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 7. xyz-directed dipole
        inp, res = GREEN3D['xyzdirdip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 2e-2, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 8. x-directed bipole
        inp, res = GREEN3D['xdirbip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)
        # 8.b Check reciprocity
        Ex = bipole(crec(inp['rec'], 0, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ey = bipole(crec(inp['rec'], 90, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ez = bipole(crec(inp['rec'], 0, 90), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 9. y-directed bipole
        inp, res = GREEN3D['ydirbip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)
        # 9.b Check reciprocity
        Ex = bipole(crec(inp['rec'], 0, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ey = bipole(crec(inp['rec'], 90, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ez = bipole(crec(inp['rec'], 0, 90), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)

        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

        # 10. z-directed bipole
        inp, res = GREEN3D['zdirbip'][()]
        Ex, Ey, Ez = get_xyz(**inp)
        par = {'rtol': 5e-3, 'atol': 1e-24, 'equal_nan': True}
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)
        # 10.b Check reciprocity
        Ex = bipole(crec(inp['rec'], 0, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ey = bipole(crec(inp['rec'], 90, 0), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        Ez = bipole(crec(inp['rec'], 0, 90), inp['src'], inp['depth'],
                    inp['res'], inp['freq'], None, inp['aniso'],
                    strength=inp['strength'], recpts=inp['srcpts'], verb=0)
        assert_allclose(Ex, res[0], **par)
        assert_allclose(Ey, res[1], **par)
        assert_allclose(Ez, res[2], **par)

    def test_empymod(self):                                       # 1.6 empymod
        # Comparison to self, to ensure nothing changed.
        # 4 bipole-bipole cases in EE, ME, EM, MM, all different values
        for i in ['1', '2', '3', '4']:
            res = DATAEMPYMOD['out'+i][()]
            tEM = bipole(**res['inp'])
            assert_allclose(tEM, res['EM'])


def test_dipole():                                                  # 2. dipole
    # As this is a shortcut, just run one test to ensure
    # it is equivalent to bipole.
    src = [5000, 1000, -200]
    rec = [0, 0, 1200]
    model = {'depth': [100, 1000], 'res': [2, 0.3, 100], 'aniso': [2, .5, 2]}
    f = 0.01
    # v  dipole : ab = 26
    # \> bipole : src-dip = 90, rec-azimuth=90, msrc=True
    dip_res = dipole(src, rec, freqtime=f, ab=26, verb=0, **model)
    bip_res = bipole([src[0], src[1], src[2], 0, 90],
                     [rec[0], rec[1], rec[2], 90, 0], msrc=True, freqtime=f,
                     verb=0, **model)
    assert_allclose(dip_res, bip_res)


def test_gpr():                                                        # 3. gpr
    # empymod is not really designed for GPR, more work on the Hankel and
    # Fourier transform would be required for that; furthermore, you would
    # rather do that straight in the time domain. However, it works. We just
    # run a test here, to check that it remains the status quo.
    res = DATAEMPYMOD['gprout'][()]
    _, gprout = gpr(**res['inp'])
    assert_allclose(gprout, res['GPR'])


def test_wavenumber():                                          # 4. wavenumber
    # This is like `frequency`, without the Hankel transform. We just run a
    # test here, to check that it remains the status quo.
    res = DATAEMPYMOD['wout'][()]
    w_res0, w_res1 = wavenumber(**res['inp'])
    assert_allclose(w_res0, res['PJ0'])
    assert_allclose(w_res1, res['PJ1'])


def test_frequency():                                            # 5. frequency
    # As this is a shortcut, just run one test to ensure
    # it is equivalent to dipole with signal=None.
    src = [100, -100, 400]
    rec = [1000, 1000, 1000]
    model = {'depth': [0, 500], 'res': [1e12, 0.3, 10], 'aniso': [1, 1, 2]}
    f = 1
    ab = 45
    f_res = frequency(src, rec, freq=f, ab=ab, verb=0, **model)
    d_res = dipole(src, rec, freqtime=f, ab=ab, verb=0, **model)
    assert_allclose(f_res, d_res)


def test_time():                                                      # 6. time
    # As this is a shortcut, just run one test to ensure
    # it is equivalent to dipole with signal!=None.
    src = [-100, 300, 600]
    rec = [1000, -500, 400]
    model = {'depth': [-100, 600], 'res': [1e12, 3, 1], 'aniso': [1, 2, 3]}
    t = 10
    ab = 51
    signal = -1
    ft = 'fftlog'
    t_res = time(src, rec, time=t, signal=signal, ab=ab, ft=ft, verb=0,
                 **model)
    d_res = dipole(src, rec, freqtime=t, signal=signal, ab=ab, ft=ft,
                   verb=0, **model)
    assert_allclose(t_res, d_res)


def test_fem():                                                        # 7. fem
    # Just ensure functionality stays the same, with one example.
    for i in ['1', '2', '3', '4', '5']:
        res = DATAFEMTEM['out'+i][()]
        fEM, kcount, _ = fem(**res['inp'])
        assert_allclose(fEM, res['EM'])
        assert kcount == res['kcount']


def test_tem():                                                        # 8. tem
    # Just ensure functionality stays the same, with one example.
    for i in ['6', '7', '8']:  # Signal = 0, 1, -1
        res = DATAFEMTEM['out'+i][()]
        tEM, _ = tem(**res['inp'])
        assert_allclose(tEM, res['EM'])
