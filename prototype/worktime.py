#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import collections

import pulp
import numpy as np
import scipy.sparse
import scipy.sparse.linalg
from pulp.solvers import GLPK

cpu_speed = np.array((1.1, 1.2, 1.3, 1.5, 2))
src_work = np.array((1, 1.3, 2, 10))

data = (1/cpu_speed).reshape((-1,1)) @ src_work.reshape((1,-1))
print(data)

speed, work = data.shape
colnum = speed + work
datapoints = speed * work

mtx_lil = scipy.sparse.lil_matrix((datapoints, colnum))
mtx_b = np.empty(shape=(datapoints,))

k = 0
for i in range(speed):
    for j in range(work):
        mtx_lil[k,i] = -1
        mtx_lil[k,speed+j] = 1
        mtx_b[k] = np.log(data[i][j])
        k += 1

mtx_csr = scipy.sparse.csr_matrix(mtx_lil)

result = scipy.sparse.linalg.lsqr(mtx_csr, mtx_b)

print(mtx_b)
print(result)

m = pulp.LpProblem("WorkerSched", pulp.LpMinimize)
assignment = {}
time_spent = [0] * speed
max_time = pulp.LpVariable("m", 0)
for j in range(work):
    row = 0
    for i in range(speed):
        assignment[i,j] = pulp.LpVariable("a_%s_%s" % (i, j), 0, cat="Binary")
        time_spent[i] += assignment[i,j] * data[i][j]
        row += assignment[i,j]
    m += row == 1
for row in time_spent:
    m += max_time >= row
m += max_time
m.writeLP('work.lp')
m.solve(GLPK())

results = []
for key, var in assignment.items():
    if round(var.varValue):
        results.append(key)

print('total_time:', pulp.value(max_time))
print(results)
