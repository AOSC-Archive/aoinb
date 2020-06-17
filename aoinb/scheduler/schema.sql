CREATE TABLE IF NOT EXISTS aoinb_machines (
    id TEXT PRIMARY KEY,
    arch TEXT,
    cpu_count INTEGER,
    mem_avail BIGINT,
    disk_avail BIGINT,
    speed DOUBLE PRECISION,
    maintainer TEXT,
    cpu_model TEXT,
    note TEXT,
    valid_from BIGINT,
    last_connected TIMESTAMP WITH TIME ZONE DEFAULT (now()),
    status INTEGER
);
CREATE TABLE IF NOT EXISTS aoinb_package_params (
    package TEXT,
    arch TEXT,
    version TEXT,
    work DOUBLE PRECISION,
    prate_slope DOUBLE PRECISION,
    prate_intercept DOUBLE PRECISION,
    mem_slope DOUBLE PRECISION,
    mem_intercept DOUBLE PRECISION,
    disk_usage BIGINT,
    updated TIMESTAMP WITH TIME ZONE DEFAULT (now()),
    PRIMARY KEY (package, arch, version)
);
CREATE TABLE IF NOT EXISTS aoinb_build_log (
    package TEXT,
    arch TEXT,
    version TEXT,
    machine_id TEXT,
    cpu_time BIGINT,  -- ns
    real_time BIGINT,  -- ns
    mem_max BIGINT,
    disk_usage BIGINT,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT (now()),
    end_time TIMESTAMP WITH TIME ZONE DEFAULT (now()),
    result TEXT,
    source TEXT,
    spec_version TEXT
);
