#!/usr/bin/tclsh
package require sqlite3

sqlite3 db [lindex $argv 0]
#db enable_load_extension 1
#db eval {SELECT load_extension('./mod_vercomp.so')}
#db enable_load_extension 0
db eval {BEGIN}
db eval {CREATE TABLE IF NOT EXISTS package_deps_all (
    package TEXT, dependency TEXT, PRIMARY KEY (package, dependency)
)}
db eval {DELETE FROM package_deps_all}
db eval {COMMIT}
set packages [db eval {SELECT DISTINCT package FROM package_dependencies}]

proc find_deps {db root name path} {
    puts $path
    if {[lsearch -exact $path $name] > -1} {return}
    set visited [db eval {
        SELECT 1 FROM t_package_deps_visited WHERE package=$name
    }]
    puts "$path"
    if {$visited ne ""} {
        foreach pkg $path {
            db eval {
                INSERT OR IGNORE INTO package_deps_all
                SELECT $pkg, dependency FROM package_deps_all
                WHERE package=$name
            }
        }
        return
    }
    set dependencies [db eval {
        SELECT DISTINCT coalesce(pr.package, pd.dependency) dependency
        FROM package_dependencies pd
        LEFT JOIN package_dependencies pr
        ON pr.dependency=pd.dependency AND pr.relationship='PKGPROV'
        WHERE pd.package=$name AND pd.architecture=''
        AND pd.relationship IN ('PKGDEP', 'BUILDDEP')
    }]
    set newpath [concat $path $name]
    foreach dep $dependencies {
        foreach pkg $newpath {
            db eval {INSERT OR IGNORE INTO package_deps_all VALUES ($pkg, $dep)}
        }
        find_deps db $root $dep $newpath
    }
    db eval {INSERT INTO t_package_deps_visited VALUES ($name)}
}

db eval {BEGIN}
db eval {CREATE TEMP TABLE t_package_deps_visited (package TEXT PRIMARY KEY)}
foreach package $packages {
    find_deps db $package $package {}
}
db eval {COMMIT}
db close
