#!/usr/bin/tclsh

set CMD_BZR bzr
if {![catch {exec which brz} result]} {set CMD_BZR brz}

proc download_SVNSRC {url path} {exec svn co $url $path >@stdout 2>@stderr}
proc update_SVNSRC {} {exec svn up >@stdout 2>@stderr}
proc checkout_SVNSRC {name branch} {
    if {$branch ne ""} {exec svn switch $branch >@stdout 2>@stderr}
    if {$name ne ""} {exec svn up -r $name >@stdout 2>@stderr}
}
proc download_GITSRC {url path} {
    exec git clone --recursive --depth 3 $url $path >@stdout 2>@stderr
}
proc update_GITSRC {} {
    exec git fetch --all --recurse-submodules=on-demand --update-shallow >@stdout 2>@stderr
}
proc checkout_GITSRC {name branch} {
    if {$name ne ""} {
        exec git checkout $name >@stdout 2>@stderr
    } else {
        exec git checkout $branch >@stdout 2>@stderr
    }
}
proc download_HGSRC {url path} {exec hg clone $url $path >@stdout 2>@stderr}
proc update_HGSRC {} {exec hg update >@stdout 2>@stderr}
proc checkout_HGSRC {name branch} {
    if {$name ne ""} {
        exec hg checkout $name >@stdout 2>@stderr
    } else {
        exec hg checkout $branch >@stdout 2>@stderr
    }
}
proc download_BZRSRC {url path} {exec $CMD_BZR branch $url $path >@stdout 2>@stderr}
proc update_BZRSRC {} {exec $CMD_BZR update >@stdout 2>@stderr}
proc checkout_BZRSRC {name branch} {
    if {$branch ne ""} {exec $CMD_BZR switch $branch >@stdout 2>@stderr}
    if {$name ne ""} {exec $CMD_BZR revert -r $name >@stdout 2>@stderr}
}
proc download_FSLSRC {url path} {
    set curdir [pwd]
    file mkdir $path
    cd $path
    exec fossil clone $url .fossil >@stdout 2>@stderr
    exec fossil open .fossil >@stdout 2>@stderr
    cd $curdir
}
proc update_FSLSRC {} {exec fossil pull >@stdout 2>@stderr}
proc checkout_FSLSRC {name branch} {
    if {$name ne ""} {
        exec fossil checkout $name >@stdout 2>@stderr
    } else {
        exec fossil checkout $branch >@stdout 2>@stderr
    }
}

proc calc_checksum {path chksumtype chksum} {
    set chksum_cmd [format "%ssum" $chksumtype]
    if {[catch {exec which $chksum_cmd} result]} {
        error "checksum $chksumtype not supported"
    }
    set result [exec $chksum_cmd $path]
    set chksum_real [lindex [split $result " "] 0]
    if {[expr {$chksum_real ne $chksum}]} {
        return $chksum_real
    } else {return ""}
}


set path [lindex $argv 0]
set linktype [lindex $argv 1]
set link [lindex $argv 2]

if {$link eq ""} {
    set script_name [info script]
    puts [format {usage: tclsh %s path SRCTBL url [chksumtype chksum]} $script_name]
    puts [format {       tclsh %s path xxxSRC url [branch [checkout]]} $script_name]
    exit 1
}

if {$linktype eq "SRCTBL"} {
    set chksumtype [lindex $argv 3]
    set chksum [lindex $argv 4]
    if {[file isfile $path] && $chksumtype ne ""} {
        if {[calc_checksum $path $chksumtype $chksum] eq ""} {
            exit 0
        } else {
            file delete -- $path
        }
    }
    exec wget -c -O $path $link >@stdout 2>@stderr
    if {$chksumtype eq ""} {exit 0}
    set chksum_real [calc_checksum $path $chksumtype $chksum]
    if {$chksum_real ne ""} {
        puts "unexpected $chksumtype $chksum_real"
        exit 1
    }
} else {
    set branch [lindex $argv 3]
    set checkout [lindex $argv 4]
    set vcs_download "download_$linktype"
    set vcs_update "update_$linktype"
    set vcs_checkout "checkout_$linktype"
    if {![file isdirectory $path]} {$vcs_download $link $path}
    set curdir [pwd]
    cd $path
    $vcs_update
    $vcs_checkout $checkout $branch
    cd $curdir
}
