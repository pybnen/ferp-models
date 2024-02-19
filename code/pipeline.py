#!/usr/bin/env python
from datetime import datetime
import sys, os, shutil, errno, subprocess, signal
import time
from argparse import ArgumentParser
import uuid

home = os.path.dirname(os.path.abspath(__file__)) + "/"
#TODO deploy my version of ijtihad in repo, use this repo in requirements.py
# use my version of ijtihad
QBFSOLVER = f"{home}../../ijtihad/ijtihad"
SATSOLVER = f"{home}picosat-965/picosat"
TRACECHECK = f"{home}booleforce-1.2/tracecheck"
TOFERP = f"{home}../../toferp/build/toferp"
FERPCHECK = f"{home}../../ferpcert/build/ferpcheck"
FERPCERT = f"{home}ferpcert2/ferpcert"
CERTCHECK = f"{home}certcheck-1.0.1/certcheck"
dependencies = [QBFSOLVER, SATSOLVER, TRACECHECK, TOFERP,  FERPCHECK, FERPCERT, CERTCHECK]

run_name = "run_" + str(uuid.uuid1()) # datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = None
keep_dir = None
keep_ferp_dir = None
tmp_dir = home + "tmp/{}/".format(run_name)


def copy_file(src, name):
  global keep_dir
  if keep_dir:
    shutil.copyfile(src, keep_dir + "/" + name)


def copy_ferp(src, name):
  global keep_ferp_dir
  if keep_ferp_dir:
    shutil.copyfile(src, keep_ferp_dir + "/" + name)


def get_log_fp():
  global log_file
  return open(log_file, 'a') if log_file is not None else open(os.devnull, 'w')


def log(msg="", prefix="*** ferpmodels: "):
  global log_file
  if log_file is None:
    return
  with open(log_file, 'a') as fp:
    fp.write(prefix + msg + "\n")
  

def assure_dir(path):
  try:
    if not os.path.exists(path):
      os.makedirs(path)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise e


def parse_args():
  global log_file, run_name, keep_dir, keep_ferp_dir
  
  parser = ArgumentParser()
  parser.add_argument("-K", "--Keep", help="keep all intermediate files in <dir>", metavar="<dir>")
  parser.add_argument("-k", "--keep", help="keep ferp proof in <dir>", metavar="<dir>")
  parser.add_argument("-l", "--log", help="Log all tool output to <dir>", metavar="<dir>")
  parser.add_argument("--no-tseitin-optimisation", default=False, action='store_true')
  parser.add_argument("--print", help="Print FERP proof", default=False, action="store_true")
  parser.add_argument("qdimacs_file", help="QBF formular in qdimacs file")
  parser.add_argument("output_file", help="Certificat file (unsat only)", default=None, nargs="?")  
  args = parser.parse_args()
  
  input_path = os.path.abspath(args.qdimacs_file)
  qbf_name = ".".join(input_path.split("/")[-1].split(".")[:-1])
  if not os.path.exists(input_path):
    raise OSError("Input file %s does not exist" % input_path)
  
  if args.Keep is not None:
    keep_dir = os.path.abspath(args.Keep)
    assure_dir(keep_dir)
    
  if args.keep is not None:
    keep_ferp_dir = os.path.abspath(args.keep)
    assure_dir(keep_ferp_dir)
  
  if args.log is not None:
    log_path = os.path.abspath(args.log)
    assure_dir(log_path)
    log_file = log_path + "/{}.log".format(run_name)
  
  output_path = None
  if args.output_file is not None:
    output_path = os.path.abspath(args.output_file)
    output_dir = "/".join(output_path.split("/")[:-1])
    assure_dir(output_dir)

  return input_path, output_path, qbf_name, args


def check_dependencies():
  for dep in dependencies:
    if not os.path.exists(dep) :
      raise OSError("One or more dependencies are missing")


def clean(ret):
  shutil.rmtree(tmp_dir, ignore_errors=True)
  sys.exit(ret)


def term_handler(signum, frame):
  print(signum, "signal handler called. Clean exit.")
  clean(-1)


def main():
  global run_name
  
  signal.signal(signal.SIGTERM, term_handler)
  signal.signal(signal.SIGINT, term_handler)

  input_path, output_path, qbf_name, args = parse_args()
  
  check_dependencies()
  assure_dir(tmp_dir)
  FNULL = open(os.devnull, 'w')
  
  log(f"run on {input_path}")
  
  # Call the qbf solver and produce the .cnf file
  log()
  log("running QBF solver")
  log()
  
  sys.stdout.write("Calling QBF solver ... ")
  sys.stdout.flush()
  
  log_fp = get_log_fp()
  start_time = time.time()
  
  call_args = [
    QBFSOLVER,
    "--wit_per_call=-1",
    "--cex_per_call=-1",
    "--tmp_dir="+tmp_dir,
    "--log_phi="+tmp_dir+"tmp.cnf",
    "--log_ksi="+tmp_dir+"tmp.cnf", # logging in case of SAT
    input_path
  ]
  
  if args.no_tseitin_optimisation:
    call_args.insert(1, '--tseitin_optimisation=0')
  
  ret = subprocess.call(call_args, stdout=log_fp)
  time_ijtihad = time.time() - start_time
  log_fp.close()
  is_sat = False
  
  copy_file(tmp_dir + "tmp.cnf", f"{run_name}.cnf")
  
  if ret == 10:
    is_sat = True
    print("DONE")
    print("The given formula is TRUE.")
    # clean(1)
  elif ret == 20:
    print("DONE")
    print("The given formula is FALSE.")
  else:
    print("FAILED")
    print("There has been an error with code %d" % ret)
    clean(2)

  assert(os.path.exists(tmp_dir + "tmp.cnf"))
  with open(tmp_dir + "tmp.cnf", "r") as f:
    if len(f.readline()) == 0:
      print("Output of Ijtihad is empty, make sure that the given qbf is not trivially true or false, e.g. it contains only existential variables.")
      clean(100)

  log()
  log("QBF solver OK")
  
  # Call the sat solver again on the .cnf file
  # This has to be done because no proof logging can be done in incremental mode
  log()
  log("running SAT solver")
  log()
  
  start_gen = time.time()

  sys.stdout.write("Calling SAT solver ... ")
  sys.stdout.flush()
  
  log_fp = get_log_fp()
  ret = subprocess.call([SATSOLVER, "-v", "-T", tmp_dir+"tmp.proof", tmp_dir+"tmp.cnf"], stdout=log_fp) #, stdout=subprocess.DEVNULL)
  log_fp.close()
  
  copy_file(tmp_dir + "tmp.proof", f"{run_name}.proof")
  
  if ret == 10:
    print("FAILED")
    print("The expanded formula is SAT")
    clean(3)
  elif ret != 20:
    print("FAILED")
    print("There has been an error with code %d" % ret)
    clean(4)
  else:
    print("DONE")

  assert (os.path.exists(tmp_dir + "tmp.proof"))

  log()
  log("SAT solver OK")
  
  # The SAT solver only produces normal extended tracecheck proofs
  # Check the proof with tracecheck and extract binary resolution proof
  log()
  log("running tracecheck")
  log()
  
  sys.stdout.write("Checking %s proof ... " % ("sat" if is_sat else "unsat")) 
  sys.stdout.flush()
  ret = subprocess.check_output([TRACECHECK, "-v", "-B", tmp_dir + "tmp.proof2", "-c", tmp_dir + "tmp.cnf", tmp_dir + "tmp.proof"])
  ret = ret.strip().decode('UTF-8')
  ret_lines = ret.split("\n")
  log(ret, "")
  
  copy_file(tmp_dir + "tmp.proof2", f"{run_name}.proof2")
  
  # if (ret == "resolved 1 root and 1 empty clause") or (ret == "resolved 0 roots and 1 empty clause" and is_sat):
  if ("resolved 1 root and 1 empty clause" in ret_lines or ("resolved 0 roots and 1 empty clause" in ret_lines and is_sat)):
    print("DONE")
  else:
    print("FAILED")
    print(ret)
    clean(5)
    
  assert (os.path.exists(tmp_dir + "tmp.proof2"))
  
  log()
  log("tracecheck OK")
      
  # Merge the comment information from the cnf and the binary resolution
  # proof into a FERP trace.
  log()
  log("producing FERP trace")
  log()
  
  sys.stdout.write("Producing FERP trace ... ")
  sys.stdout.flush()
  log_fp = get_log_fp()
  start_toferp = time.time()
  ret = subprocess.call([TOFERP, tmp_dir + "tmp.cnf", tmp_dir + "tmp.proof2", tmp_dir + "tmp.ferp"], stdout=log_fp)
  end_toferp = time.time()
  log_fp.close()
  
  copy_file(tmp_dir + "tmp.ferp", f"{run_name}.ferp")
  copy_ferp(tmp_dir + "tmp.ferp", f"{run_name}.ferp")
  
  time_toferp = end_toferp - start_toferp
  time_gen = end_toferp - start_gen
    
  if ret != 0:
    print("FAILED", ret)
    clean(6)
  else:
    print("DONE")
    
  log()
  log("FERP trace OK")

  # Check whether the FERP trace is consistent
  log()
  log("checking FERP trace")
  log()
  
  sys.stdout.write("Checking FERP trace ...")
  sys.stdout.flush()
  
  log_fp = get_log_fp()
  start_time = time.time()
  ret = subprocess.call([FERPCHECK, input_path, tmp_dir + "tmp.ferp"], stdout=log_fp)
  time_ferpcheck = time.time() - start_time
  log_fp.close()
  
  if ret != 0:
    print("FAILED", ret)
    clean(7)
  else:
    print("DONE")
    
  log()
  log("FERP trace valid")
  
  log()
  log("PYTHON-TIMES")
  log()
  log(f"Solver:      {time_ijtihad:.6f} s", "")
  log(f"Generation:  {time_gen:.6f} s", "")
  log(f"ToFerp:      {time_toferp:.6f} s", "")
  log(f"FerpCheck:   {time_ferpcheck:.6f} s", "")
  log()
  log("PYTHON-TIMES")

  print("PYTHON-TIMES------------------------------")
  print(f"Solver:      {time_ijtihad:.6f} s")
  print(f"Generation:  {time_gen:.6f} s")
  print(f"ToFerp:      {time_toferp:.6f} s")
  print(f"FerpCheck:   {time_ferpcheck:.6f} s")
  print("------------------------------------------")

  if args.print:
    with open(tmp_dir + "tmp.ferp") as ferp_fp:
      print(ferp_fp.read())
  
  if output_path is None or is_sat:
    clean(0)
  
  # Extract a circuit for the universals into an AIGER file

  sys.stdout.write("Extracting strategy ... ")
  sys.stdout.flush()
  ret = subprocess.call([FERPCERT, input_path, tmp_dir + "tmp.ferp", output_path])

  if ret != 0:
    print("FAILED", ret)
    clean(8)
  else:
    print("DONE")

  # Merge AIGER and QDIMACS files into a formula checkable by a SAT solver

  sys.stdout.write("Producing CNF ... ")
  sys.stdout.flush()

  FCNF = open(tmp_dir + "tmp.cnf2", "wb")
  ret = subprocess.call([CERTCHECK, input_path, output_path], stdout=FCNF)
  FCNF.close()
  
  copy_file(tmp_dir + "tmp.cnf2", f"{run_name}.cnf2")
  
  if ret != 0:
    print("FAILED", ret)
    clean(9)
  else:
    print("DONE")

  sys.stdout.write("Check validity of certificate ... ")
  sys.stdout.flush()
  ret = subprocess.call([SATSOLVER, tmp_dir + "tmp.cnf2"],
                        stdout=FNULL, stderr=FNULL)
  if ret == 10:
    print("FAILED")
    print("The merged formula is SAT")
    clean(10)
  elif ret != 20:
    print("FAILED")
    print("There has been an error with code %d" % ret)
    clean(11)
  else:
    print("SUCCESS")
    subprocess.call(["gzip", output_path])
    clean(0)


if __name__ == '__main__':
  main()
