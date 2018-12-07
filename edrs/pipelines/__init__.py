import os
import logging
logger = logging.getLogger(__name__)
import configparser

import numpy as np
import astropy.io.fits as fits
import matplotlib.pyplot as plt
import matplotlib.ticker as tck

from ..utils.obslog import read_log, find_log
from ..utils.misc   import write_system_info

from . import common
from . import xinglong216hrs
from . import foces
from . import levy
from . import sarg

#from .reduction import Reduction

def reduce_echelle():
    '''Automatically select the instrument and reduce echelle spectra
    accordingly.

    Available instruments include:
        
        * *FOCES*: FOCES on 2m Fraunhofer Telescope in Wendelstein Observatory,
            Germany.
        * *Xinglong216HRS*: HRS on 2.16m telescope in Xinglong Station, China.

    '''

    # initialize running log
    log_fmt = ' '.join(['*',
                        '%(asctime)s.%(msecs)03d',
                        '[%(levelname)s]',
                        '%(name)s - %(lineno)d - %(funcName)s():'+os.linesep,
                        ' %(message)s'+os.linesep+'-'*80,
                        ])
    logging.basicConfig(filename='edrs.log',level=logging.DEBUG,
            format=log_fmt, datefmt='%Y-%m-%dT%H:%M:%S')
    logger = logging.getLogger(__name__)

    # write system info
    write_system_info()

    # load config file in current directory
    config_file_lst = [fname for fname in os.listdir(os.curdir)
                        if fname[-4:]=='.cfg']
    config = configparser.ConfigParser(
                inline_comment_prefixes = (';','#'),
                interpolation           = configparser.ExtendedInterpolation(),
                )
    config.read(config_file_lst)

    # find telescope and instrument from config file
    section = config['data']
    telescope  = section['telescope']
    instrument = section['instrument']

    logger.info('Start reducing %s, %s data'%(telescope, instrument))

    if telescope == 'Fraunhofer' and instrument == 'FOCES':
        foces.reduce()
    elif telescope == 'Xinglong216' and instrument == 'HRS':
        xinglong216hrs.reduce()
    elif telescope == 'APF' and instrument == 'Levy':
        levy.reduce()
    else:
        print('Unknown Instrument: %s - %s'%(telescope, instrument))
        exit()

def make_log():
    '''Scan the path to the raw FITS files and generate an observing log.
    '''
    config_file_lst = []

    # find local config file
    for fname in os.listdir(os.curdir):
        if fname[-4:]=='.cfg':
            config_file_lst.append(fname)

    # load both built-in and local config files
    config = configparser.ConfigParser(
                inline_comment_prefixes = (';','#'),
                interpolation           = configparser.ExtendedInterpolation(),
                )
    config.read(config_file_lst)

    section = config['data']
    telescope  = section['telescope']
    instrument = section['instrument']
    rawdata    = section['rawdata']

    if telescope == 'Fraunhofer' and instrument == 'FOCES':
        foces.make_log(rawdata)
    elif telescope == 'Xinglong216' and instrument == 'HRS':
        xinglong216hrs.make_log(rawdata)
    elif telescope == 'APF' and instrument == 'Levy':
        levy.make_log(rawdata)
    else:
        print('Unknown Instrument: %s - %s'%(telescope, instrument))
        exit()

def show_spectra1d(filename_lst):
    '''Show 1-D spectra in a pop-up window.

    Args:
        filename_lst (list): List of filenames of 1-D spectra.
    '''
    spec_lst = []
    for filename in filename_lst:
        data = fits.getdata(filename)
        spec = {}
        for row in data:
            order = row['order']
            wave  = row['wavelength']
            flux  = row['flux']
            spec[order] = (wave, flux)
        spec_lst.append(spec)

    fig = plt.figure(figsize=(15, 8), dpi=150)
    ax = fig.add_axes([0.07, 0.1, 0.88, 0.8])

    def plot_order(order):
        ax.cla()
        ax.currentorder = order
        wave_min, wave_max = 1e9, 0
        flux_min = 1e9
        for i, spec in enumerate(spec_lst):
            if order in spec:
                wave = spec[order][0]
                flux = spec[order][1]
                ax.plot(wave, flux, '-', alpha=0.8, lw=0.8,
                        label=os.path.basename(filename_lst[i]))
                wave_min = min(wave_min, wave.min())
                wave_max = max(wave_max, wave.max())
                flux_min = min(flux_min, flux.min())
        leg = ax.legend(loc='upper right')
        leg.get_frame().set_alpha(0.1)
        ax.set_xlabel(u'Wavelength (\xc5)', fontsize=12)
        ax.set_ylabel('Flux', fontsize=12)
        ax.set_title('Order %d'%(order), fontsize=14)
        ax.set_xlim(wave_min, wave_max)
        ax.axhline(y=0, color='k', ls='--', lw=0.5)
        if flux_min > 0:
            ax.set_ylim(0,)
        ax.xaxis.set_major_formatter(tck.FormatStrFormatter('%g'))
        ax.yaxis.set_major_formatter(tck.FormatStrFormatter('%g'))
        fig.canvas.draw()

    def on_key(event):
        if event.key == 'up':
            can_plot = False
            for spec in spec_lst:
                if ax.currentorder + 1 in spec:
                    can_plot=True
                    break
            if can_plot:
                plot_order(ax.currentorder + 1)
        elif event.key == 'down':
            can_plot = False
            for spec in spec_lst:
                if ax.currentorder - 1 in spec:
                    can_plot=True
                    break
            if can_plot:
                plot_order(ax.currentorder - 1)
        else:
            pass

    order0 = list(spec_lst[0].keys())[0]
    plot_order(order0)

    fig.canvas.mpl_connect('key_press_event', on_key)
    plt.show()
