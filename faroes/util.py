import numpy as np
from math import pi as π
from scipy.special import ellipe, hyp2f1

from plasmapy.particles import Particle, common_isotopes
from plasmapy.particles import atomic_number, isotopic_abundance


def most_common_isotope(sp):
    """A Particle of the most common isotope and
    maximum charge for the given species.

    Parameters
    ----------
    sp : str
       Element name or symbol of the species

    Returns
    -------
    Particle
    """
    isotopes = common_isotopes(sp)
    max_charge = atomic_number(sp)
    abundances = []
    for i in isotopes:
        abundances.append(isotopic_abundance(i))
    isotope_index = np.argmax(abundances)
    most_common_isotope = isotopes[isotope_index]
    mass_number = Particle(most_common_isotope).mass_number
    impurity = Particle(max_charge, Z=max_charge, mass_numb=mass_number)
    return impurity


def tube_segment_volume(r_i, r_o, h):
    """Volume of a finite tube's wall
    """
    V = π * (r_o**2 - r_i**2) * h
    return V


def tube_segment_volume_derivatives(r_i, r_o, h):
    """Derivatives for volume of a finite tube's wall
    """
    dVdr_i = -2 * π * h * r_i
    dVdr_o = 2 * π * h * r_o
    dVdh = π * (r_o**2 - r_i**2)
    return {'r_i': dVdr_i, 'r_o': dVdr_o, 'h': dVdh}


def ellipse_perimeter_simple(a, b):
    """Often seen as √((1 + κ^2)/2)

    Parameters
    ----------
    a : float
       short minor radius of an ellipse
    b : float
       long minor radius of an ellipse

    Returns
    -------
    P : float
       perimeter of the ellipse
    """
    P = 2 * π * a * np.sqrt((1 + (b / a)**2) / 2)
    return P


def ellipse_perimeter(a, b):
    """Exact formula using special functions

    Parameters
    ----------
    a : float
       one minor radius of an ellipse
    b : float
       other minor radius of an ellipse

    Returns
    -------
    P : float
       perimeter of the ellipse
    """
    return 4 * b * ellipe(1 - a**2 / b**2)


def ellipse_perimeter_derivatives(a, b):
    """Exact formula using special functions

    Parameters
    ----------
    a : float
       one minor radius of an ellipse
    b : float
       other minor radius of an ellipse

    Returns
    -------
    Dict of
    a : float
       derivative with respect to a
    b : float
       derivative with respect to b

    Notes
    -----
    We use a different form here to avoid zeros in denominators when a==b

    Mathematica:
    D[\[Pi] Sqrt[2 (a^2 + b^2)]
    Hypergeometric2F1[-(1/4), 1/4, 1, (a^2 - b^2)^2/(a^2 + b^2)^2], a]
    """
    def epd(a, b):
        hyp1 = hyp2f1(-1 / 4, 1 / 4, 1, ((a**2 - b**2) / (a**2 + b**2))**2)
        num1 = 2**(1 / 2) * a * π * hyp1
        den1 = (a**2 + b**2)**(1 / 2)
        term1 = num1 / den1

        hyp2 = hyp2f1(3 / 4, 5 / 4, 2, ((a**2 - b**2) / (a**2 + b**2))**2)
        num2 = 8 * a * (a - b) * b**2 * (a + b) / (a**2 + b**2)**3 * π
        num2 = num2 * hyp2 * (a**2 + b**2)**(1 / 2)
        den2 = 8 * 2**(1 / 2)
        term2 = num2 / den2
        return term1 - term2

    dPda = epd(a, b)
    dPdb = epd(b, a)  # formula is symmetric
    return {'a': dPda, 'b': dPdb}


def ellipse_perimeter_ramanujan(a, b):
    """Surprisingly accurate formula for ellipse perimeter

    Parameters
    ----------
    a : float
       one minor radius of an ellipse
    b : float
       other minor radius of an ellipse

    Returns
    -------
    P : float
       perimeter of the ellipse
    """
    P = π * (3 * (a + b) - np.sqrt((3 * a + b) * (3 * b + a)))
    return P


def ellipse_perimeter_ramanujan_derivatives(a, b):
    """Partial derivatives for ellipse_perimeter_ramanujan
    """
    dPda = π * (3 - (3 * a + 5 * b) / np.sqrt((3 * a + b) * (a + 3 * b)))
    dPdb = π * (3 - (5 * a + 3 * b) / np.sqrt((3 * a + b) * (a + 3 * b)))
    return {'a': dPda, 'b': dPdb}


def torus_surface_area(R, a, b=None):
    """Simple formula for surface area of a (elliptical) torus

    Parameters
    ----------
    R : float
       major radius
    a : float
       horizontal minor radius
    b : float [optional]
       vertical minor radius

    Returns
    -------
    sa : float
        Surface area
    """
    if b is not None:
        circumference = ellipse_perimeter_ramanujan(a, b)
    else:
        circumference = 2 * π * a
    sa = 2 * π * R * circumference
    return sa


def torus_volume(R, a, b=None):
    """Volume of a (elliptical) torus

    Parameters
    ----------
    R : float
       major radius
    a : float
       horizontal minor radius
    b : float [optional]
       vertical minor radius

    Returns
    -------
    V : float
        Volume
    """
    if b is None:
        b = a
    area = π * a * b
    circum = 2 * π * R
    V = area * circum
    return V
