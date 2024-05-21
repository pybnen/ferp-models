#!/usr/bin/env python

import subprocess

# List of file paths to process
file_list = [
#"../../qbf-benchmarks/qbflib/Biere/Counter/cnt12.qdimacs.gz",
#"../../qbf-benchmarks/qbflib/Biere/Counter/cnt12r.qdimacs.gz",
#"../../qbf-benchmarks/qbflib/Biere/Counter/cnt13.qdimacs.gz",
#"../../qbf-benchmarks/fuzz_search/fuzz_s3_v500_c600/593cfa72-816a-4e82-ab0e-9d8e53190785.qdimacs",
#"../../qbf-benchmarks/fuzz_search/fuzz_s3_v500_c600/0cf6034f-407f-442a-857e-d438253583fc.qdimacs",
#"../../qbf-benchmarks/fuzz_search/fuzz_s3_v600_c600/8a32014e-5829-420b-93d8-48f48cd4308b.qdimacs",
#"../../qbf-benchmarks/fuzz_search/fuzz_s3_v600_c600/a6a7427b-7b1e-46c0-8cbc-8a427e0be673.qdimacs",
#"../../qbf-benchmarks/fuzz_search/fuzz_s3_v500_c600/04c87193-4f61-4581-afcf-ccc3506caf6f.qdimacs",
#"../../qbf-benchmarks/qbfgallery23/incrementer-enc06-nonuniform-depth-33.qdimacs.gz",
#"../../qbf-benchmarks/qbfgallery23/opt18_problem05_length_2.qdimacs.gz",
#"../../qbf-benchmarks/qbfgallery23/sat18_problem03_length_3.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c1_BMC_p1_k2048.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c1_Debug_s3_f2_e1_v1.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c1_Debug_s5_f1_e1_v2.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c2_Debug_s3_f1_e1_v2.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c2_Debug_s3_f2_e1_v3.qdimacs.gz",
"../../qbf-benchmarks/qbfgallery23/c6_BMC_p1_k2048.qdimacs.gz"
]

# Base paths for log and keep directories
log_base_path = "../../ferp-testing/"
keep_base_path = "../../ferp-testing/"

# Iterate over each file and execute the command
for file_path in file_list:
    # Extract the filename without the path and extension
    filename = file_path.split('/')[-1].split('.')[0]
    print(filename)
    
    # Construct the log and keep paths
    log_path = f"{log_base_path}{filename}"
    keep_path = f"{keep_base_path}{filename}"
    
    # Construct the command
    command = ["./pipeline.py", file_path, "--log", log_path, "--Keep", keep_path]
    
    # Execute the command
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully processed {file_path}")
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error processing {file_path}")
        print(e.stderr.decode())