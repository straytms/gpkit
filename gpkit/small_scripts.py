import numpy as np

from collections import defaultdict
from collections import Iterable

from .small_classes import HashVector
from .small_classes import Strings, Quantity


def diff(p, vk):
    exps, cs = [], []
    from . import units as ureg
    units = vk.descr.get("units", 1) if ureg else 1
    for i, exp in enumerate(p.exps):
        exp = HashVector(exp)
        if vk in exp:
            e = exp[vk]
            if e == 1:
                del exp[vk]
            else:
                exp[vk] -= 1
            exps.append(exp)
            cs.append(e*p.cs[i]/units)
    return exps, cs


def mono_approx(p, x0):
    if not x0:
        for i, exp in enumerate(p.exps):
            if exp == {}:
                return p.cs[i], {}
    exp = HashVector()
    p0 = p.sub(x0).c
    m0 = 1
    from . import units as ureg
    for vk in p.varlocs:
        units = vk.descr.get("units", 1) if ureg else 1
        e = mag(x0[vk]*units * p.diff(vk).sub(x0, require_positive=False).c / p0)
        exp[vk] = e
        m0 *= (x0[vk]*units)**e
    return p0/m0, exp


def isequal(a, b):
    if (isinstance(a, Iterable) and
            not isinstance(a, Strings+(tuple, list, dict))):
        for i, a_i in enumerate(a):
            if not isequal(a_i, b[i]):
                return False
    elif a != b:
        return False
    return True


def mag(c):
    "Return magnitude of a Number or Quantity"
    if isinstance(c, Quantity):
        return c.magnitude
    else:
        return c


def unitstr(units, into="%s", options="~", dimless='-'):
    if hasattr(units, "descr"):
        if isinstance(units.descr, dict):
            units = units.descr.get("units", dimless)
    if units and not isinstance(units, Strings):
        try:
            rawstr = ("{:%s}" % options).format(units)
        except:
            rawstr = "1.0 " + str(units.units)
        units = "".join(rawstr.replace("dimensionless", dimless).split()[1:])
    if units:
        return into % units
    else:
        return ""


def is_sweepvar(sub):
    "Determines if a given substitution indicates a sweep."
    try:
        if sub[0] == "sweep":
            if isinstance(sub[1], Iterable) or hasattr(sub[1], "__call__"):
                return True
    except:
        return False


def invalid_types_for_oper(oper, a, b):
    "Raises TypeError for unsupported operations."
    typea = a.__class__.__name__
    typeb = b.__class__.__name__
    raise TypeError("unsupported operand types"
                    " for %s: '%s' and '%s'" % (oper, typea, typeb))


def latex_num(c):
    cstr = "%.4g" % c
    if 'e' in cstr:
        idx = cstr.index('e')
        cstr = "%s \\times 10^{%i}" % (cstr[:idx], int(cstr[idx+1:]))
    return cstr


def locate_vars(exps):
    "From exponents form a dictionary of which monomials each variable is in."
    varlocs = defaultdict(list)
    varkeys = defaultdict(set)
    for i, exp in enumerate(exps):
        for var in exp:
            varlocs[var].append(i)
            varkeys[var.name].add(var)

    varkeys_ = dict(varkeys)
    for name, varl in varkeys_.items():
        for vk in varl:
            descr = vk.descr
            break
        if "shape" in descr:
            # vector var
            newlist = np.zeros(descr["shape"], dtype="object")
            for var in varl:
                newlist[var.descr["idx"]] = var
            varkeys[name] = newlist
        else:
            if len(varl) == 1:
                varkeys[name] = varl.pop()
            else:
                varkeys[name] = []
                for var in varl:
                    if "model" in var.descr:
                        varkeys[name+"_%s" % var.descr["model"]] = var
                    else:
                        varkeys[name].append(var)
                if len(varkeys[name]) == 1:
                    varkeys[name] = varkeys[name][0]
                elif len(varkeys[name]) == 0:
                    del varkeys[name]

    return dict(varlocs), dict(varkeys)


def sort_and_simplify(exps, cs, return_map=False):
    """Reduces the number of monomials, and casts them to a sorted form.

    Arguments
    ---------

    exps : list of Hashvectors
        The exponents of each monomial
    cs : array of floats or Quantities
        The coefficients of each monomial
    return_map : bool (optional)
        Whether to return the map of which monomials combined to form a
        simpler monomial, and their fractions of that monomial's final c.

    Returns
    -------

    exps : list of Hashvectors
        Exponents of simplified monomials.
    cs : array of floats or Quantities
        Coefficients of simplified monomials.
    mmap : list of tuples
        List for each original monomial of (destination index, fraction)
    """
    matches = defaultdict(float)
    if return_map:
        expmap = defaultdict(dict)
    for i, exp in enumerate(exps):
        exp = HashVector({var: x for (var, x) in exp.items() if x != 0})
        matches[exp] += cs[i]
        if return_map:
            expmap[exp][i] = cs[i]

    if len(matches) > 1:
        zeroed_terms = (exp for exp, c in matches.items() if c == 0)
        for exp in zeroed_terms:
            del matches[exp]

    exps_ = tuple(matches.keys())
    cs_ = list(matches.values())
    if isinstance(cs_[0], Quantity):
        units = cs_[0]/cs_[0].magnitude
        cs_ = [c.to(units).magnitude for c in cs_] * units
    else:
        cs_ = np.array(cs_, dtype='float')

    if not return_map:
        return exps_, cs_
    else:
        mmap = [None]*len(cs)
        for i, item in enumerate(matches.items()):
            exp, c = item
            for j in expmap[exp]:
                mmap[j] = (i, expmap[exp][j]/c)
        return exps_, cs_, mmap


def flatten(ible, classes):
    """Flatten an iterable that contains other iterables

    Arguments
    ---------
    l : Iterable
        Top-level container

    Returns
    -------
    out : list
        List of all objects found in the nested iterables

    Raises
    ------
    TypeError
        If an object is found whose class was not in classes
    """
    out = []
    for el in ible:
        if isinstance(el, classes):
            out.append(el)
        elif isinstance(el, Iterable):
            for elel in flatten(el, classes):
                out.append(elel)
        else:
            raise TypeError("Iterable %s contains element '%s'"
                            " of invalid class %s." % (ible, el, el.__class__))
    return out
