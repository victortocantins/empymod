"""Routines to create data from external modellers, for comparison purposes.

- DIPOLE1D: You must have Dipole1D installed and it must be in your system
  path; http://software.seg.org/2012/0003.

- EMmod: You must have Dipole1D installed and it must be in your system
  path; http://software.seg.org/2015/0001.

- Green3D: You must have Green3D installed (for which you need to be a member
  of the CEMI consortium). The following files must be in the folder
  `empymod/tests/green3d`: `green3d.m`, `grint.mexa64`,
  `grint.mexw64`,`normal.mexa64`, and `normal.mexw64`. Furthermore, you need
  Matlab.

Tested only on Linux (Ubuntu 16.04 LTS, x86_64).

"""
import os
import subprocess
import numpy as np
from scipy.constants import mu_0
from os.path import join, dirname


class ChDir(object):
    """Step into a directory temporarily.

    Taken from:
    pythonadventures.wordpress.com/2013/12/15/
                    chdir-a-context-manager-for-switching-working-directories

    """

    def __init__(self, path):
        self.old_dir = os.getcwd()
        self.new_dir = path

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, *args):
        os.chdir(self.old_dir)


def green3d(src, rec, depth, res, freq, aniso, par, strength=0):
    """Run model with green3d (CEMI).

    You must have Green3D installed (for which you need to be a member of the
    CEMI consortium). The following files must be in the folder
    `empymod/tests/green3d`:
        - `green3d.m`
        - `grint.mexa64`
        - (`grint.mexw64`)
        - (`normal.mexa64`)
        - (`normal.mexw64`).
    Furthermore, you need to have Matlab installed.

    http://www.cemi.utah.edu

    """

    # Execution directory
    # (no need to create it, it HAS to exist with the necessary green3d-files).
    rundir = join(dirname(__file__), 'green3d/')

    # Source-input depending on par
    if par in [9, 10]:
        srcstr = str(src[0]) + ' ' + str(src[1]) + ' ' + str(src[2]) + ' '
        srcstr += str(src[3]) + ' ' + str(src[4])
    elif par in [2, 3]:
        srcstr = str(strength) + ' ' + str(src[0]) + ' ' + str(src[2]) + ' '
        srcstr += str(src[4]) + ' ' + str(src[1]) + ' ' + str(src[3]) + ' '
        srcstr += str(src[5])
    elif par in [6, 7, 8]:
        srcstr = str(src[0]) + ' ' + str(src[1]) + ' ' + str(src[2])

    # Write input file
    with open(rundir + 'run.sh', 'wb') as runfile:

        runfile.write(bytes(
            '#!/bin/bash\n\nmatlab -nodesktop -nosplash -r "[e, h] = green3d('
            '[' + ','.join(map(str, freq))+'], '
            '[' + ','.join(map(str, depth[1:] - np.r_[0, depth[1:-1]])) + '], '
            '[' + ','.join(map(str, 1/res[1:])) + '], '
            '[' + ','.join(map(str, aniso[1:])) + '], '
            '[' + ','.join(map(str, rec[0].ravel())) + '], '
            '[' + ','.join(map(str, rec[1].ravel())) + '], '
            '[' + ','.join(map(str, np.ones(np.size(rec[0])) * rec[2])) + '], '
            '[' + str(par) + ' ' + srcstr + ']); exit"', 'UTF-8'))

    # Run Green3D
    with ChDir(rundir):
        subprocess.run('bash run.sh', shell=True,
                       stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    # Read output-file
    with open(rundir + 'out.txt', 'rb') as outfile:
        temp = np.loadtxt(outfile)

        Ex = temp[:, 0] + 1j*temp[:, 1]
        Ey = temp[:, 2] + 1j*temp[:, 3]
        Ez = temp[:, 4] + 1j*temp[:, 5]
        Hx = temp[:, 6] + 1j*temp[:, 7]
        Hy = temp[:, 8] + 1j*temp[:, 9]
        Hz = temp[:, 10] + 1j*temp[:, 11]

        if par in [6, 7, 8, 10]:
            Ex /= 2j*freq*np.pi*mu_0
            Ey /= 2j*freq*np.pi*mu_0
            Ez /= 2j*freq*np.pi*mu_0
            Hx /= 2j*freq*np.pi*mu_0
            Hy /= 2j*freq*np.pi*mu_0
            Hz /= 2j*freq*np.pi*mu_0

        return Ex, Ey, Ez, Hx, Hy, Hz


def dipole1d(src, rec, depth, res, freq, strength=0):
    """Run model with dipole1d (Scripps).

    You must have Dipole1D installed and it must be in your system path.

    http://software.seg.org/2012/0003

    """

    # Create directory, overwrite existing
    rundir = join(dirname(__file__), 'dipole1d/')
    os.makedirs(rundir, exist_ok=True)

    # Source: A bipole in dipole1d is defined as: center point, angles, length
    if len(src) == 6:
        dx = src[1] - src[0]
        dy = src[3] - src[2]
        dz = src[5] - src[4]
        r = np.sqrt(dx**2 + dy**2 + dz**2)
        theta = np.rad2deg(np.arctan2(dy, dx))
        phi = np.rad2deg(np.pi/2-np.arccos(dz/r))
        src = [src[0]+dx/2, src[2]+dy/2, src[4]+dz/2, theta, phi]
    else:
        r = 0  # 0 = dipole

    # Angle: In empymod, x is Easting, and the angle is the deviation from x
    #        anticlockwise.  In Dipole1D, x is Northing, and the angle is the
    #        deviation from x clockwise. Convert angle to within 0<=ang<360:
    ang = (-src[3] % - 360 + 90) % 360

    # Write input file
    with open(rundir + 'RUNFILE', 'wb') as runfile:
        runfile.write(bytes(
            'Version:          DIPOLE1D_1.0\n'
            'Output Filename:  dipole1d.csem\n'
            'CompDerivatives:  no\n'
            'HT Filters:       kk_ht_401\n'
            'UseSpline1D:      no\n'
            'Dipole Length:    '+str(r)+'\n'
            '# TRANSMITTERS:   '+str(np.size(src[2]))+'\n'
            '          X           Y           Z    ROTATION         DIP\n',
            'UTF-8'))
        np.savetxt(runfile, np.atleast_2d(np.r_[src[1], src[0], src[2], ang,
                   src[4]]), fmt='%12.4f')
        runfile.write(bytes('# FREQUENCIES:    '+str(np.size(freq))+'\n',
                      'UTF-8'))
        np.savetxt(runfile, freq, fmt='%10.3f')
        runfile.write(bytes('# LAYERS:         '+str(np.size(res))+'\n',
                      'UTF-8'))
        np.savetxt(runfile, np.r_[[np.r_[-1000000, depth]], [res]].transpose(),
                   fmt='%12.5g')
        runfile.write(bytes('# RECEIVERS:      '+str(np.size(rec[0]))+'\n',
                      'UTF-8'))
        rec = np.r_[[rec[1].ravel()], [rec[0].ravel()],
                    [np.ones(np.size(rec[0]))*rec[2]]]
        np.savetxt(runfile, rec.transpose(), fmt='%12.4f')

    # Run dipole1d
    with ChDir(rundir):
        subprocess.run('DIPOLE1D', shell=True,
                       stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    # Read output-file
    with open(rundir + 'RUNFILE', 'rb') as infile:
        nlines = np.int(sum(1 for line in infile))

    with open(rundir + 'dipole1d.csem', 'rb') as outfile:
        temp = np.loadtxt(outfile, skiprows=nlines-5, unpack=True)
        Ex = temp[0] - 1j*temp[1]
        Ey = temp[2] - 1j*temp[3]
        Ez = temp[4] - 1j*temp[5]
        Hx = temp[6]/mu_0 - 1j*temp[7]/mu_0
        Hy = temp[8]/mu_0 - 1j*temp[9]/mu_0
        Hz = temp[10]/mu_0 - 1j*temp[11]/mu_0

    return Ey, Ex, Ez, Hy, Hx, Hz
