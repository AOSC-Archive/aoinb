#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import sqlite3
import operator
import itertools
import collections

import pulp
from pulp.solvers import GLPK

M = 1000000

CONTAINER_RECIPE = frozenset(
    "admin-base core-base editor-base python-base network-base "
    "systemd-base web-base util-base".split()
)
BUILDKIT_RECIPE = CONTAINER_RECIPE | frozenset(
    "devel-base debug-base git autobuild3 acbs".split())


def get_package_deps(cur, package):
    cur.execute("""
        SELECT DISTINCT coalesce(pr.package, pd.dependency) dependency
        FROM package_dependencies pd
        LEFT JOIN package_dependencies pr
        ON pr.dependency=pd.dependency AND pr.relationship='PKGPROV'
        WHERE pd.package=? AND pd.architecture=''
        AND pd.relationship IN ('PKGDEP', 'BUILDDEP')
    """, (package,))
    return [row[0] for row in cur]

def find_all_deps(cur, deps, visited, name, path=()):
    if name in path:
        return
    if name in visited:
        for pkg in path:
            deps[pkg].update(deps[name])
        return
    dependencies = get_package_deps(cur, name)
    newpath = path + (name,)
    for dep in dependencies:
        for pkg in newpath:
            deps[pkg].add(dep)
        find_all_deps(cur, deps, visited, dep, newpath)
    visited.add(name)

def get_all_package_deps(cur):
    package_deps_all = collections.defaultdict(set)
    visited = set()
    packages = [row[0] for row in cur.execute(
        "SELECT DISTINCT package FROM package_dependencies")]
    for name in packages:
        find_all_deps(cur, package_deps_all, visited, name)
    return package_deps_all


db = sqlite3.connect(sys.argv[1])

model = pulp.LpProblem("GCD", pulp.LpMaximize)
obj = 0
includes = {}
valids = {}
usages = {}
commons = []

print('Loading packages...')

cur = db.cursor()
all_pkgs = set()
for row in cur.execute("SELECT name FROM packages"):
    name = row[0]
    includes[name] = pulp.LpVariable("x_%s" % name, 0, cat="Binary")
    valids[name] = pulp.LpVariable("v_%s" % name, 0, cat="Binary")
    all_pkgs.add(name)

print('Loading full package dependencies...')

all_pkg_deps = get_all_package_deps(cur)

#print(len(all_pkg_deps['qbittorrent']))
#print(sorted(all_pkg_deps['qbittorrent']))
#print(len(all_pkg_deps['telegram-desktop']))

print('Loading individual package dependencies...')

pkg_deps = {}
pkg_dep_usages = {}
ignored_deps = set()

for package in all_pkgs:
    deps = set()
    constr_row = 0
    dep_usages = 0
    for dep in get_package_deps(cur, package):
        if dep not in all_pkgs:
            print('%s -> %s not found' % (package, dep))
            continue
        deps.add(dep)
        constr_row += includes[dep]
        usages[package, dep] = pulp.LpVariable(
            "u_%s_%s" % (package, dep), 0, cat="Binary")
        dep_usages += usages[package, dep]
    pkg_dep_usages[package] = dep_usages
    obj += dep_usages
    pkg_deps[package] = deps
    if package in BUILDKIT_RECIPE:
        ignored_deps.add(package)
        ignored_deps.update(all_pkg_deps[package])
    model += constr_row >= len(deps) * includes[package]

#print('Loading full dependencies...')

#cur.execute(
    #"SELECT package, dependency FROM package_deps_all "
    #"ORDER BY package, dependency"
#)
#pkg_deps = {}
#pkg_dep_usages = {}
#ignored_deps = set()
#for package, group in itertools.groupby(cur, key=operator.itemgetter(0)):
    #deps = set()
    #constr_row = 0
    #dep_usages = 0
    #for row in group:
        #dep = row[1]
        #if dep not in all_pkgs:
            #print('%s -> %s not found' % (package, dep))
            #continue
        #deps.add(dep)
        #constr_row += includes[dep]
        #usages[package, dep] = pulp.LpVariable(
            #"u_%s_%s" % (package, dep), 0, cat="Binary")
        #dep_usages += usages[package, dep]
    #pkg_dep_usages[package] = dep_usages
    #obj += dep_usages
    #pkg_deps[package] = deps
    #if package in BUILDKIT_RECIPE:
        #ignored_deps.add(package)
        #ignored_deps.update(deps)
    #model += constr_row == len(deps) * includes[package]

print('Making including constraints...')

_ig1 = operator.itemgetter(1)

for dep, group in itertools.groupby(sorted(usages.keys(), key=_ig1), key=_ig1):
    row = pulp.lpSum(usages[key] for key in group)
    model += M * includes[dep] >= row
    model += includes[dep] <= row

print('Making excluding constraints...')

nondeps_all = all_pkgs.difference(ignored_deps)
for package, deps in all_pkg_deps.items():
    if package not in valids:
        continue
    elif not deps:
        model += valids[package] == 0
        continue
    nondeps = nondeps_all.difference(deps)
    nondeps.discard(package)
    vrow = pulp.LpVariable("ndep_%s" % package)
    commons.append(vrow)
    row = pulp.lpSum(includes[key] for key in nondeps)
    model += vrow == row
    model += M - M * valids[package] >= vrow
    model += 1 - valids[package] <= vrow
    model += M * valids[package] >= pkg_dep_usages[package]

model += obj

print('Solving...')

model.writeLP('gcd.lp')
model.solve(GLPK('glpsol', options=['--cuts']))

obj_value = pulp.value(model.objective)
print('Obj: %s' % obj_value)
print('Includes: =============')
for pkg, var in includes.items():
    if round(var.varValue):
        print(pkg)
print('Valid for: =============')
for pkg, var in valids.items():
    if round(var.varValue or 0):
        print(pkg)
