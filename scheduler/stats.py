#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time
import sqlite3
import operator
import itertools

try:
    import numpy as np
    import scipy.sparse
    import scipy.sparse.linalg
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class BuildStatistics:
    ref_package = 'glibc'
    default_speed = 0.001
    default_work = 1

    def __init__(self, dbconn):
        self.db = sqlite3.connect(dbconn)

    def init_db(self):
        cur = self.db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS aoinb_machines ("
            "id TEXT PRIMARY KEY,"
            "arch TEXT,"
            "cpu_count INTEGER,"
            "mem_avail INTEGER,"
            "disk_avail INTEGER,"
            "speed REAL,"
            "maintainer TEXT,"
            "note TEXT,"
            "valid_from INTEGER,"
            "updated INTEGER"
        ")")
        cur.execute("CREATE TABLE IF NOT EXISTS aoinb_package_params ("
            "package TEXT,"
            "arch TEXT,"
            "version TEXT,"
            "work REAL,"
            "prate_slope REAL,"
            "prate_intercept REAL,"
            "mem_max INTEGER,"
            "disk_usage INTEGER,"
            "updated INTEGER,"
            "PRIMARY KEY (package, arch, version)"
        ")")
        cur.execute("CREATE TABLE IF NOT EXISTS aoinb_build_log ("
            "package TEXT,"
            "arch TEXT,"
            "version TEXT,"
            "machine_id TEXT,"
            "cpu_time INTEGER,"  # (ns)
            "real_time INTEGER,"  # (ns)
            "mem_max INTEGER,"
            "disk_usage INTEGER,"
            "start_time INTEGER"
            "end_time INTEGER"
            "result TEXT,"
            "source TEXT,"
            "spec_version TEXT"
        ")")
        self.db.commit()

    def calc_params(self):
        cur = self.db.cursor()
        avg_speeds = {}
        for arch, speed in cur.execute(
            "SELECT arch, avg(speed) FROM aoinb_machines GROUP BY arch"):
            avg_speeds[arch] = speed
        avg_work = {}
        for package, arch, work in cur.execute(
            "SELECT package, arch, avg(work) "
            "FROM aoinb_package_params GROUP BY package, arch"):
            avg_work[package, arch] = work
        cur.execute("""
        SELECT
          bl.package, bl.arch, bl.version, bl.machine_id,
          bl.cpu_time, bl.real_time, bl.mem_max, bl.disk_usage, am.cpu_count
        FROM aoinb_build_log bl
        INNER JOIN aoinb_machines am
        ON bl.machine_id = am.id
        AND bl.start_time > am.valid_from
        WHERE bl.result = 'success'
        ORDER BY bl.package, bl.arch, bl.version, bl.machine_id, bl.start_time DESC
        """)
        machines = {}
        machine_num = 0
        packages = {}
        package_num = 0
        v_machines = {}
        w_packages = {}
        p_packages = {}
        package_params = {}
        data = {}
        for pkg_key, group in itertools.groupby(cur, operator.itemgetter(0, 1, 2)):
            max_mem = max_disk = 0
            last_machine = None
            packages[pkg_key] = package_num
            w_packages[pkg_key] = avg_work.get(pkg_key[:2], self.default_work)
            prates = []
            for row in group:
                (package, arch, version, machine_id,
                 cpu_time, real_time, mem, disk, cpu_count) = row
                if mem:
                    max_mem = max(max_mem, mem)
                if disk:
                    max_disk = max(max_disk, disk)
                prates.append((cpu_count, max(0, (cpu_time/real_time - 1))))
                if machine_id != last_machine:
                    v_machines[machine_id] = avg_speeds.get(
                        arch, self.default_speed)
                    machine_idx = machines.get(machine_id, machine_num)
                    if machine_idx == machine_num:
                        machines[machine_id] = machine_num
                        machine_num += 1
                    data[machine_idx, package_num] = cpu_time / 1e9
                last_machine = machine_id
            p_packages[pkg_key] = self._estimate_prate_params(prates)
            package_params[pkg_key] = (max_mem, max_disk)
            package_num += 1
        if SCIPY_AVAILABLE:
            results = self._estimate_params(
                data, machines, packages)
            v_machines.update(results[0])
            w_packages.update(results[1])
        for machine_id, value in v_machines.items():
            cur.execute("UPDATE aoinb_machines SET speed=? WHERE id=?",
                        (value, machine_id))
        for key, value in w_packages.items():
            prate_k, prate_b = p_packages[key]
            upd = (int(time.time()),)
            cur.execute(
                "INSERT OR REPLACE INTO aoinb_package_params "
                "(package, arch, version, work, prate_slope, prate_intercept, "
                " mem_max, disk_usage, updated) VALUES (?,?,?,?,?,?,?,?,?)",
                key + (value, prate_k, prate_b) + package_params[key] + upd
            )
        self.db.commit()

    def _estimate_prate_params(self, prates):
        if not prates:
            return 0, 0
        elif len(prates) == 1:
            return 0, prates[0][1]
        if SCIPY_AVAILABLE:
            arr = np.array(prates).T
            if np.all(arr[1]) == 0:
                return 0, 0
            result = scipy.stats.linregress(arr[0], arr[1])
            return result[:2]
        else:
            total_num = total_prate = 0
            for num, prate in prates:
                total_num += num
                total_prate += prate * num
            return 0, total_prate / total_num

    def _estimate_params(self, data, machines, packages):
        ref_pkg_idx = packages.get(self.ref_package)
        machine_num = len(machines)
        package_num = len(packages)
        colnum = machine_num + package_num
        datapoints = len(data)
        data_keys = [None] * datapoints
        if ref_pkg_idx is not None:
            datapoints += 1
        mtx_dok = scipy.sparse.dok_matrix((datapoints, colnum))
        mtx_b = np.empty(shape=(datapoints,))
        if ref_pkg_idx is not None:
            mtx_dok[-1, machine_num+ref_pkg_idx] = 1
            mtx_b[-1] = 0
        for k, row in enumerate(data.items()):
            machine_idx, package_idx = data_keys[k] = row[0]
            mtx_dok[k, machine_idx] = -1
            mtx_dok[k, machine_num+package_idx] = 1
            mtx_b[k] = math.log(row[1])
        matrix = mtx_dok.tocsr()
        result = scipy.sparse.linalg.lsqr(matrix, mtx_b)
        result_params = np.exp(result[0])
        v_machines = {}
        w_packages = {}
        for name, idx in machines.items():
            v_machines[name] = result_params[idx]
        for name, idx in packages.items():
            w_packages[name] = result_params[machine_num+idx]
        return v_machines, w_packages
