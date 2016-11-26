"""

:mod:`transform` -- Hankel and Fourier Transforms
=================================================

Methods to carry out the required Hankel transform from wavenumber to
frequency domain and Fourier transform from frequency to time domain.

The functions for the QWE and FHT Hankel and Fourier transforms are based on
source files (specified in each function) from the source code distributed with
[Key_2012]_, which can be found at `software.seg.org/2012/0003
<http://software.seg.org/2012/0003>`_. These functions are (c) 2012 by Kerry
Key and the Society of Exploration Geophysicists,
http://software.seg.org/disclaimer.txt. Please read the NOTICE-file in the root
directory for more information regarding the involved licenses.

"""
# Copyright 2016 Dieter Werthmüller
#
# This file is part of `empymod`.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations under
# the License.


import numpy as np
from scipy.special import jv
from scipy.integrate import quad
from scipy.interpolate import InterpolatedUnivariateSpline as iuSpline

from . import kernel

__all__ = ['fht', 'hqwe', 'fft', 'fqwe', 'fftlog', 'qwe', 'get_Gauss_Weights',
           'get_spline_values', 'fhti']


# 1. Hankel transforms (wavenumber -> frequency)


def fht(zsrc, zrec, lsrc, lrec, off, angle, depth, ab, etaH, etaV, zetaH,
        zetaV, xdirect, fhtarg, use_spline, use_ne_eval, msrc, mrec):
    """Hankel Transform using the Fast Hankel Transform.

    The *Fast Hankel Transform* is a *Digital Filter Method*, introduced to
    geophysics by [Gosh_1971]_, and made popular and wide-spread by
    [Anderson_1975]_, [Anderson_1979]_, [Anderson_1982]_.

    This implementation of the FHT follows [Key_2012]_, equation 6.  Without
    going into the mathematical details (which can be found in any of the above
    papers) and following [Key_2012]_, the FHT method rewrites the Hankel
    transform of the form

    .. math:: F(r)   = \int^\infty_0 f(\lambda)J_v(\lambda r)\
            \mathrm{d}\lambda

    as

    .. math::   F(r)   = \sum^n_{i=1} f(b_i/r)h_i/r \ ,

    where :math:`h` is the digital filter.The Filter abscissae b is given by

    .. math:: b_i = \lambda_ir = e^{ai}, \qquad i = -l, -l+1, \cdots, l \ ,

    with :math:`l=(n-1)/2`, and :math:`a` is the spacing coefficient.

    This function is loosely based on `get_CSEM1D_FD_FHT.m` from the source
    code distributed with [Key_2012]_.

    The function is called from one of the modelling routines in :mod:`model`.
    Consult these modelling routines for a description of the input and output
    parameters.

    Returns
    -------
    fEM : array
        Returns frequency-domain EM response.

    """
    # Get fhtargs
    fhtfilt = fhtarg[0]
    ndec = fhtarg[1]

    # For FHT, spline for one offset is equals no spline
    if use_spline and off.size == 1:
        use_spline = False

    # 1. COMPUTE REQUIRED LAMBDAS for given hankel-filter-base
    if use_spline:           # Use interpolation
        # Get lambda from offset and filter
        lambd, ioff = get_spline_values(fhtfilt, off, ndec)

    else:  # df.base/off
        lambd = fhtfilt.base/off[:, None]

    # 2. CALL THE KERNEL
    PJ0, PJ1, PJ0b = kernel.wavenumber(zsrc, zrec, lsrc, lrec, depth, etaH,
                                       etaV, zetaH, zetaV, lambd, ab, xdirect,
                                       msrc, mrec, use_ne_eval)

    if use_spline and ndec:  # If spline in wavenumber domain, interpolate PJ's
        # Interpolate in wavenumber domain
        PJ0real = iuSpline(np.log(lambd), PJ0.real)
        PJ0imag = iuSpline(np.log(lambd), PJ0.imag)
        PJ1real = iuSpline(np.log(lambd), PJ1.real)
        PJ1imag = iuSpline(np.log(lambd), PJ1.imag)
        PJ0breal = iuSpline(np.log(lambd), PJ0b.real)
        PJ0bimag = iuSpline(np.log(lambd), PJ0b.imag)

        # Overwrite lambd with non-spline lambd
        lambd = fhtfilt.base/off[:, None]

        # Get fEM-field at required non-spline lambdas
        PJ0 = PJ0real(np.log(lambd)) + 1j*PJ0imag(np.log(lambd))
        PJ1 = PJ1real(np.log(lambd)) + 1j*PJ1imag(np.log(lambd))
        PJ0b = PJ0breal(np.log(lambd)) + 1j*PJ0bimag(np.log(lambd))

        # Set spline to false
        use_spline = False

    elif use_spline:  # If spline in frequency domain, re-arrange PJ's
        def rearrange_PJ(PJ, noff, nfilt):
            """Return re-arranged PJ with shape (noff, nlambd).
               Each row starts one 'lambda' higher."""
            outarr = np.concatenate((np.tile(PJ, noff).squeeze(),
                                    np.zeros(noff)))
            return outarr.reshape(noff, -1)[:, :nfilt]

        PJ0 = rearrange_PJ(PJ0, ioff.size, fhtfilt.base.size)
        PJ1 = rearrange_PJ(PJ1, ioff.size, fhtfilt.base.size)
        PJ0b = rearrange_PJ(PJ0b, ioff.size, fhtfilt.base.size)

    # 3. ANGLE DEPENDENT FACTORS
    factAng = kernel.angle_factor(angle, ab, msrc, mrec)
    one_angle = (factAng - factAng[0] == 0).all()

    # 4. CARRY OUT THE FHT
    if use_spline and one_angle:  # SPLINE, ALL ANGLES ARE EQUAL
        # If all offsets are in one line from the source, hence have the same
        # angle, we can combine PJ0 and PJ0b and save one FHT, and combine both
        # into one function to interpolate.

        # 1. FHT
        EM_int = factAng[0]*np.dot(PJ1, fhtfilt.j1)
        if ab in [11, 12, 21, 22, 14, 24, 15, 25]:  # Because of J2
            # J2(kr) = 2/(kr)*J1(kr) - J0(kr)
            EM_int /= ioff
        EM_int += np.dot(PJ0 + factAng[0]*PJ0b, fhtfilt.j0)

        # 2. Interpolation
        real_EM = iuSpline(np.log(ioff[::-1]), EM_int.real[::-1])
        imag_EM = iuSpline(np.log(ioff[::-1]), EM_int.imag[::-1])
        fEM = real_EM(np.log(off)) + 1j*imag_EM(np.log(off))

    elif use_spline:  # SPLINE, VARYING ANGLES
        # If not all offsets are in one line from the source, hence do not have
        # the same angle, the whole process has to be done separately for
        # angle-dependent and angle-independent parts. This means one FHT more,
        # and two (instead of one) functions to interpolate.

        # 1. FHT
        # Separated in an angle-dependent and a non-dependent part
        EM_noang = np.dot(PJ0, fhtfilt.j0)
        EM_angle = np.dot(PJ1, fhtfilt.j1)
        if ab in [11, 12, 21, 22, 14, 24, 15, 25]:  # Because of J2
            # J2(kr) = 2/(kr)*J1(kr) - J0(kr)
            EM_angle /= ioff
        EM_angle += np.dot(PJ0b, fhtfilt.j0)

        # 2. Interpolation
        # Separately on EM_noang and EM_angle
        real_noang = iuSpline(np.log(ioff[::-1]), EM_noang.real[::-1])
        imag_noang = iuSpline(np.log(ioff[::-1]), EM_noang.imag[::-1])
        real_angle = iuSpline(np.log(ioff[::-1]), EM_angle.real[::-1])
        imag_angle = iuSpline(np.log(ioff[::-1]), EM_angle.imag[::-1])

        # Get fEM-field at required offsets
        EM_noang = real_noang(np.log(off)) + 1j*imag_noang(np.log(off))
        EM_angle = real_angle(np.log(off)) + 1j*imag_angle(np.log(off))

        # Angle dependency
        fEM = (factAng*EM_angle + EM_noang)

    else:  # NO SPLINE
        # Without spline, we can combine PJ0 and PJ0b to save one FHT, even if
        # all offsets have a different angle.
        fEM = factAng*np.dot(PJ1, fhtfilt.j1)
        if ab in [11, 12, 21, 22, 14, 24, 15, 25]:  # Because of J2
            # J2(kr) = 2/(kr)*J1(kr) - J0(kr)
            fEM /= off
        fEM += np.dot(PJ0 + factAng[:, np.newaxis]*PJ0b, fhtfilt.j0)

    # Return the electromagnetic field, normalize by offset
    return fEM/off


def hqwe(zsrc, zrec, lsrc, lrec, off, angle, depth, ab, etaH, etaV, zetaH,
         zetaV, xdirect, qweargs, use_spline, use_ne_eval, msrc, mrec):
    """Hankel Transform using Quadrature-With-Extrapolation.

    *Quadrature-With-Extrapolation* was introduced to geophysics by
    [Key_2012]_. It is one of many so-called *ISE* methods to solve Hankel
    Transforms, where *ISE* stands for Integration, Summation, and
    Extrapolation.

    Following [Key_2012]_, but without going into the mathematical details
    here, the QWE method rewrites the Hankel transform of the form

    .. math:: F(r)   = \int^\infty_0 f(\lambda)J_v(\lambda r)\
            \mathrm{d}\lambda

    as a quadrature sum which form is similar to the FHT (equation 15),

    .. math::   F_i   \\approx \sum^m_{j=1} f(x_j/r)w_j g(x_j) =
                \sum^m_{j=1} f(x_j/r)\hat{g}(x_j) \ ,

    but with various bells and whistles applied (using the so-called Shanks
    transformation in the form of a routine called :math:`\epsilon`-algorithm
    ([Shanks_1955]_, [Wynn_1956]_; implemented with algorithms from
    [Trefethen_2000]_ and [Weniger_1989]_).

    This function is based on `get_CSEM1D_FD_QWE.m`, `qwe.m`,
    `getGaussQuadWeights.m`, and `getBesselWeights.m` from the source code
    distributed with [Key_2012]_.

    The function is called from one of the modelling routines in :mod:`model`.
    Consult these modelling routines for a description of the input and output
    parameters.

    Returns
    -------
    fEM : array
        Returns frequency-domain EM response.

    """
    # Input params have an additional dimension for frequency, reduce here
    etaH = etaH[0, :]
    etaV = etaV[0, :]
    zetaH = zetaH[0, :]
    zetaV = zetaV[0, :]

    # Get rtol, atol, nquad, maxint, and pts_per_dec
    rtol, atol, nquad, maxint, pts_per_dec = qweargs

    # ** 1. PRE-COMPUTE THE BESSEL FUNCTIONS
    #    at fixed quadrature points for each interval and multiply by the
    #    corresponding Gauss quadrature weights

    # ** 1.a COMPUTE GAUSS QUADRATURE WEIGHTS
    g_x, g_w = get_Gauss_Weights(nquad)

    # ** 1.b COMPUTES N ZEROS OF THE BESSEL FUNCTION OF THE FIRST KIND
    #    of order 1 using the Newton-Raphson method, which is fast enough for
    #    our purposes.

    # Initial guess using asymptotic zeros
    b_zero = np.pi*np.arange(1.25, maxint+1)

    # Newton-Raphson iterations
    for i in range(10):   # 10 is more than enough, usually stops in 5

        # Evaluate
        b_x0 = jv(1, b_zero)
        b_x1 = jv(2, b_zero)

        # The step length
        b_h = -b_x0/(b_x0/b_zero - b_x1)

        # Take the step
        b_zero += b_h

        # Check for convergence
        if all(np.abs(b_h) < 8*np.finfo(float).eps*b_zero):
            break

    # ** 1.c COMPUTES THE QUADRATURE INTERVALS AND BESSEL FUNCTION WEIGHTS

    # Lower limit of integrand, a small but non-zero value
    xint = np.concatenate((np.array([1e-20]), b_zero))

    # Assemble the output arrays
    dx = np.repeat(np.diff(xint)/2, nquad)
    Bx = dx*(np.tile(g_x, maxint) + 1) + np.repeat(xint[:-1], nquad)
    BJ0 = jv(0, Bx)*np.tile(g_w, maxint)
    BJ1 = jv(1, Bx)*np.tile(g_w, maxint)

    # ** 2. START QWE

    # Intervals and lambdas for all offset
    intervals = xint/off[:, None]
    lambd = Bx/off[:, None]

    # Angle dependent factors
    factAng = kernel.angle_factor(angle, ab, msrc, mrec)

    # Call and return QWE, depending if spline or not
    if use_spline:  # If spline, we calculate all kernels here
        # New lambda, from min to max required lambda with pts_per_dec
        start = np.log(lambd.min())
        stop = np.log(lambd.max())
        ilambd = np.logspace(start, stop, (stop-start)*pts_per_dec + 1, 10)

        # Call the kernel
        PJ0, PJ1, PJ0b = kernel.wavenumber(zsrc, zrec, lsrc, lrec, depth,
                                           etaH[None, :], etaV[None, :],
                                           zetaH[None, :], zetaV[None, :],
                                           np.atleast_2d(ilambd), ab, xdirect,
                                           msrc, mrec, use_ne_eval)

        # Interpolation : Has to be done separately on each PJ,
        # in order to work with multiple offsets which have different angles.
        si_PJ0r = iuSpline(np.log(ilambd), PJ0.real)
        si_PJ0i = iuSpline(np.log(ilambd), PJ0.imag)
        si_PJ1r = iuSpline(np.log(ilambd), PJ1.real)
        si_PJ1i = iuSpline(np.log(ilambd), PJ1.imag)
        si_PJ0br = iuSpline(np.log(ilambd), PJ0b.real)
        si_PJ0bi = iuSpline(np.log(ilambd), PJ0b.imag)

        # Get EM-field at required offsets
        sPJ0 = si_PJ0r(np.log(lambd))+1j*si_PJ0i(np.log(lambd))
        sPJ1 = si_PJ1r(np.log(lambd))+1j*si_PJ1i(np.log(lambd))
        sPJ0b = si_PJ0br(np.log(lambd))+1j*si_PJ0bi(np.log(lambd))

        # Carry out and return the Hankel transform for this interval
        sEM = np.sum(np.reshape(sPJ1*BJ1, (off.size, nquad, -1), order='F'), 1)
        if ab in [11, 12, 21, 22, 14, 24, 15, 25]:  # Because of J2
            # J2(kr) = 2/(kr)*J1(kr) - J0(kr)
            sEM /= np.atleast_1d(off[:, np.newaxis])
        sEM += np.sum(np.reshape(sPJ0b*BJ0, (off.size, nquad, -1),
                                 order='F'), 1)
        sEM *= factAng[:, np.newaxis]
        sEM += np.sum(np.reshape(sPJ0*BJ0, (off.size, nquad, -1),
                                 order='F'), 1)

        getkernel = sEM
        # Parameters not used if spline
        lambd = None
        off = None
        factAng = None

    else:  # If not spline, we define the wavenumber-kernel here
        def getkernel(i, inplambd, inpoff, inpfang):
            """Return wavenumber-domain-kernel as a fct of interval i."""

            # Indices and factor for this interval
            iB = i*nquad + np.arange(nquad)

            # PJ0 and PJ1 for this interval
            PJ0, PJ1, PJ0b = kernel.wavenumber(zsrc, zrec, lsrc, lrec, depth,
                                               etaH[None, :], etaV[None, :],
                                               zetaH[None, :], zetaV[None, :],
                                               np.atleast_2d(inplambd)[:, iB],
                                               ab, xdirect, msrc, mrec,
                                               use_ne_eval)

            # Carry out and return the Hankel transform for this interval
            fEM = inpfang*np.dot(PJ1[0, :], BJ1[iB])
            if ab in [11, 12, 21, 22, 14, 24, 15, 25]:  # Because of J2
                # J2(kr) = 2/(kr)*J1(kr) - J0(kr)
                fEM /= np.atleast_1d(inpoff)
            fEM += inpfang*np.dot(PJ0b[0, :], BJ0[iB])
            fEM += np.dot(PJ0[0, :], BJ0[iB])

            return fEM

    # Get QWE
    fEM = qwe(rtol, atol, maxint, getkernel, intervals, 'Hankel', lambd, off,
              factAng)

    return fEM


# 2. Fourier transforms (frequency -> time)

def fft(fEM, time, freq, ftarg):
    """Fourier Transform using a Cosine- or a Sine-filter.

    It follows the Filter methodology [Anderson_1975]_, see `fht` for more
    information.

    The function is called from one of the modelling routines in :mod:`model`.
    Consult these modelling routines for a description of the input and output
    parameters.

    This function is based on `get_CSEM1D_TD_FHT.m` from the source code
    distributed with [Key_2012]_.

    Returns
    -------
    tEM : array
        Returns time-domain EM response of `fEM` for given `time`.

    """
    # Get ftarg values
    fftfilt, ftkind, pts_per_dec = ftarg

    # Settings depending if cos/sin plus scaling
    if ftkind == 'sin':
        fEM = -fEM.imag
    else:
        fEM = fEM.real

    if pts_per_dec:  # Use pts_per_dec frequencies per decade
        # 1. Interpolate in frequency domain
        sfEM = iuSpline(np.log(2*np.pi*freq), fEM)
        ifEM = sfEM(np.log(fftfilt.base/time[:, None]))

        # 2. Filter
        tEM = np.dot(ifEM, getattr(fftfilt, ftkind))

    else:  # Standard FHT procedure
        # Get new times in frequency domain
        _, itime = get_spline_values(fftfilt, time)

        # Re-arranged fEM with shape (ntime, nfreq).  Each row starts one
        # 'freq' higher.
        fEM = np.concatenate((np.tile(fEM, itime.size).squeeze(),
                             np.zeros(itime.size)))
        fEM = fEM.reshape(itime.size, -1)[:, :fftfilt.base.size]

        # 1. Filter
        stEM = np.dot(fEM, getattr(fftfilt, ftkind))

        # 2. Interpolate in time domain
        itEM = iuSpline(np.log((itime)[::-1]), stEM[::-1])
        tEM = itEM(np.log(time))

    # Return the electromagnetic time domain field
    return tEM/time


def fqwe(fEM, time, freq, qweargs):
    """Fourier Transform using Quadrature-With-Extrapolation.

    It follows the QWE methodology [Key_2012]_ for the Hankel transform, see
    `hqwe` for more information.

    The function is called from one of the modelling routines in :mod:`model`.
    Consult these modelling routines for a description of the input and output
    parameters.

    This function is based on `get_CSEM1D_TD_QWE.m` from the source code
    distributed with [Key_2012]_.

    Returns
    -------
    tEM : array
        Returns time-domain EM response of `fEM` for given `time`.

    """
    # Get rtol, atol, nquad, and maxint
    rtol, atol, nquad, maxint, _ = qweargs

    # Calculate quadrature intervals for all offset
    xint = np.concatenate((np.array([1e-20]), np.arange(1, maxint+1)*np.pi))
    intervals = xint/time[:, None]

    # Get Gauss Quadrature Weights
    g_x, g_w = get_Gauss_Weights(nquad)
    dx = np.repeat(np.diff(xint)/2, nquad)
    Bx = dx*(np.tile(g_x, maxint) + 1) + np.repeat(xint[:-1], nquad)
    SS = np.sin(Bx)*np.tile(g_w, maxint)

    # Interpolate in frequency domain
    tEM_rint = iuSpline(np.log(2*np.pi*freq), fEM.real)
    tEM_iint = iuSpline(np.log(2*np.pi*freq), fEM.imag)

    # Check if we use QWE or SciPy's Quad
    check = np.log(intervals[:, 1])
    doqwe = np.abs(fEM[0])/np.abs(tEM_rint(check) + 1j*tEM_iint(check)) < 100

    # Pre-allocate output array
    tEM = np.zeros(time.size)

    # Carry out SciPy's Quad if required
    if np.any(~doqwe):
        def sEMquad(w, t):
            """Return scaled, interpolated value of tEM_iint for `w`."""
            return tEM_iint(np.log(w))*np.sin(w*t)

        # Loop over times that require Quad
        for i in np.where(~doqwe)[0]:
            tEM[i], _ = quad(sEMquad, intervals[i, 0], intervals[i, -1],
                             (time[i],), 0, atol, rtol, limit=500)

    # Carry out QWE if required
    if np.any(doqwe):
        sEM = tEM_iint(np.log(Bx/time[doqwe, None]))*SS
        tEM[doqwe] = qwe(rtol, atol, maxint, sEM, intervals[doqwe, :],
                         'Fourier')

    return -tEM


def fftlog(fEM, time, freq, ftarg):
    """Fourier Transform using FFTLog.

    FFTLog is the logarithmic analogue to the Fast Fourier Transform FFT.
    FFTLog was presented in Appendix B of [Hamilton_2000]_ and published at
    <http://casa.colorado.edu/~ajsh/FFTLog>.

    This function uses the python module `fftlog`, which is a simple
    `f2py`-wrapper for the Fortran code `FFTLog`. You need to install `fftlog`
    separately on your system in order to use it, see
    <https://github.com/prisae/fftlog>.

    The function is called from one of the modelling routines in :mod:`model`.
    Consult these modelling routines for a description of the input and output
    parameters.

    Returns
    -------
    tEM : array
        Returns time-domain EM response of `fEM` for given `time`.

    """
    # Get r, rk, wsave, fftlog
    r, rk, wsave, fftlog = ftarg

    # Carry out FFTLog
    ttEM = fftlog.fftl(-fEM.imag, 1, wsave, rk)

    # Interpolate for the desired times
    int_tEM = iuSpline(np.log10(r), ttEM)
    tEM = int_tEM(np.log10(time))

    return tEM


# 3. Utilities

def qwe(rtol, atol, maxint, inp, intervals, hfstr, lambd=None, off=None,
        factAng=None):
    """Quadrature-With-Extrapolation.

    This is the kernel of the QWE method, used for the Hankel (`hqwe`) and the
    Fourier (`fqwe`) Transforms. See `hqwe` for an extensive description.

    This function is based on `qwe.m` from the source code distributed with
    [Key_2012]_.

    """
    def getweights(i, inpint):
        """Return weights for this interval."""
        return (np.atleast_2d(inpint)[:,  i+1] - np.atleast_2d(inpint)[:, i])/2

    # 2.a Calculate the first interval for all offsets
    if hasattr(inp, '__call__'):  # Hankel and not spline
        EM0 = inp(0, lambd, off, factAng)
    else:                         # Fourier or Hankel with spline
        EM0 = inp[:, 0]
    EM0 *= getweights(0, intervals)

    # 2.b pre-allocate arrays
    EM = np.zeros(EM0.size, dtype=EM0.dtype)
    om = np.ones(EM0.size, dtype=bool)
    S = np.zeros((EM0.size, maxint), dtype=EM0.dtype)
    relErr = np.zeros((EM0.size, maxint))
    extrap = np.zeros((EM0.size, maxint), dtype=EM0.dtype)

    # 2.c the extrapolation transformation loop
    old_settings = np.seterr(all='ignore')
    for i in range(1, maxint):
        im = np.mod(i, 2)

        # 2.c.1. calculate the field for this interval
        if hasattr(inp, '__call__'):  # Hankel and not spline
            EMi = inp(i, lambd[om, :], off[om], factAng[om])
        else:                         # Fourier or Hankel with spline
            EMi = inp[om, i]
        EMi *= getweights(i, intervals[om, :])

        # 2.c.2. compute shanks transformation
        # using the epsilon algorithm; structured after [weniger_1989]_, p26.
        S[:, i][om] = S[:, i-1][om] + EMi  # working array for transformation

        # recursive loop
        aux2 = np.zeros(om.sum(), dtype=EM0.dtype)
        for k in range(i, 0, -1):
            aux1, aux2 = aux2, S[om, k-1]
            ddff = S[om, k] - aux2
            S[om, k-1] = np.where(np.abs(ddff) < np.finfo(np.double).tiny,
                                  np.finfo(np.double).max, aux1 + 1/ddff)

        # the extrapolated result plus the first interval term
        extrap[om, i-1] = S[om, im] + EM0[om]

        # 2.c.3. analyze for convergence
        if i > 1:
            # Calculate relative and absolute error
            rErr = (extrap[om, i-1] - extrap[om, i-2])/extrap[om, i-1]
            relErr[om, i-1] = np.abs(rErr)
            abserr = atol/np.abs(extrap[om, i-1])

            # Update booleans
            om[om] *= relErr[om, i-1] >= rtol + abserr

            # Store in EM
            EM[om] = extrap[om, i-1]

        if (~om).all():
            break

    # Warning if maxint is potentially too small
    if i+1 == maxint:
        print('* WARNING :: ' + hfstr + '-QWE used all ' + str(maxint) +
              ' intervals; set `maxint` higher.')

    # Catch the ones that did not converge
    EM[om] = extrap[om, i-1]
    np.seterr(**old_settings)

    # Set np.finfo(np.double).max to 0
    EM.real[EM.real == np.finfo(np.double).max] = 0

    return EM


def get_Gauss_Weights(nquad):
    """Return Gauss Quadrature Weights of order nquad on the interval [-1, 1].

    Algorithm from page 129 in [Trefethen_2000]_.

    This function is based on `getGaussQuadWeights.m` from the source code
    distributed with [Key_2012]_.

    """
    g_beta = 1/np.sqrt(4 - 1/(np.arange(1, nquad)*np.arange(1, nquad)))
    g_d, g_v = np.linalg.eig(np.diag(g_beta, 1) + np.diag(g_beta, -1))
    g_i = np.argsort(g_d, axis=0)
    g_x = g_d[g_i]
    g_w = 2*g_v[0, g_i]*g_v[0, g_i]
    return g_x, g_w


def get_spline_values(filt, inp, nr_per_dec=None):
    """Return required calculation points."""

    # If number per decade (nr_per_dec) is not provided, filter.factor is used
    if not nr_per_dec:
        nr_per_dec = 1/np.log(filt.factor)

    # Get min and max required out-values (depends on filter and inp-value)
    outmax = filt.base[-1]/inp.min()
    outmin = filt.base[0]/inp.max()

    # Number of out-values
    nout = int(np.ceil(np.log(outmax/outmin)*nr_per_dec) + 1)

    # Calculate output values
    out = np.exp(np.arange(np.log(outmin), np.log(outmin) + nout/nr_per_dec,
                           1/nr_per_dec))

    # Only necessary if standard spline is used. We need to calculate the new
    # input values, as spline is carried out in the input domain. Else spline
    # is carried out in output domain and the new input values are not used.
    new_inp = inp.max()*np.exp(-np.arange(nout - filt.base.size + 1) /
                               nr_per_dec)

    # Return output values
    return np.atleast_2d(out), new_inp


def fhti(mu, rmin, rmax, n, fftlog, kr=1, q=0, kropt=1):
    """Return parameters required for FFTLog."""

    # Central point log10(r_c) of periodic interval
    logrc = (rmin + rmax)/2

    # Central index (1/2 integral if n is even)
    nc = (n + 1)/2.

    # Log spacing of points
    dlogr = (rmax - rmin)/n
    dlnr = dlogr*np.log(10.)

    # Get optimal kr and wsave
    kr, wsave, _ = fftlog.fhti(n, mu, dlnr, kr=kr, q=q, kropt=kropt)

    # Calculate required input x-values (r)
    r = 10**(logrc + (np.arange(1, n+1) - nc)*dlogr)

    # Calculate k with adjusted kr
    logkc = np.log10(kr) - logrc
    k = 10**(logkc + (np.arange(1, n+1) - nc)*dlogr)

    # rk = r_c/k_r
    rk = 10**(logrc - logkc)

    return r, k, wsave, rk