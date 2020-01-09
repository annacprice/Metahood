from __future__ import print_function
from __future__ import division

try:
    from future_builtins import zip
except:
    pass

from subprocess import Popen, PIPE
import os
import os.path
from os.path import basename
import re


default_values = {
    "binning":{"concoct":{"contig_size" : 1000,"execution" : 1,"max_bin_nb" : 5000},"metabat2":{"execution" : 0,"contig_size":1500}},
    "mag":["native"],
    "threads":8,
    "assembly":    {"assembler": "megahit","groups": {},"parameters":"" },
    "annotation":{},
    'cat_db':"",
    "kraken_db":"",
    "graph":{"List_graphs":{}},
    "samples":{"setup":0},
    "Percent_memory":0.5,
    "maganalysis":0,
    "desman":{"execution":0, "nb_haplotypes": 10,"nb_repeat": 5,"min_cov": 1,"scripts":""}
}

# ---- neat regex matching of files --------
def extended_glob(pattern):
    process = Popen(['bash -O extglob -c " ls -d '+pattern+'/ "'], stdout=PIPE, stderr=PIPE,shell=True)
    List_path=[element[:-1] for element in process.communicate()[0].decode("utf-8").split("\n") if element]
    return [path for path in List_path if basename(path)!="multiqc_data"]


# Taken from http://stackoverflow.com/questions/36831998/how-to-fill-default-parameters-in-yaml-file-using-python
def setdefault_recursively(tgt, default = default_values):
    for k in default:
        if isinstance(default[k], dict): # if the current item is a dict,
            # expand it recursively
            setdefault_recursively(tgt.setdefault(k, {}), default[k])
        else:
            # ... otherwise simply set a default value if it's not set before
            tgt.setdefault(k, default[k])

def fill_default_values(config):
    local_dir = config.get("LOCAL_DIR")
    if local_dir:
        default_values["scripts"] = os.path.join(local_dir, "scripts")
        default_values["scg_data"]= os.path.join(local_dir, "scg_data")
        default_values["conda_env"]= os.path.join(local_dir, "Conda_envs")
    setdefault_recursively(config)

def sample_name(fullname):
    return os.path.splitext(os.path.basename(fullname))[0]

# FASTA_EXTS = {".fastq", ".fastq.gz"}  # only 2 extension are valid. 
FASTA_EXTS = {".fastq.gz"}  # only extension valid. 
def get_extension(file) :
    for ext in FASTA_EXTS:
        if file.endswith(ext):
            return ext 

def gather_paths(path, basename=False):
    for filename in os.listdir(path):
        name = os.path.basename(filename)
        for ext in FASTA_EXTS:
            if not name.endswith(ext):
                continue
            filepath = os.path.join(path, filename)
            if basename:
                yield (name[0:-len(ext)], filepath)
            else:
                yield filepath

def detect_reads(dir):
    return sorted(list(gather_paths(dir)))

#Autodetect references
def gather_refs(data):
    if type(data) is list:
        for path in data:
            for ref in gather_refs(path):
                yield ref
    else:
        if data.startswith("@"):
            with open(data[1:]) as input:
                for ref in load_dict(input).items():
                    yield ref
        elif os.path.isdir(data):
            for ref in gather_paths(data, True):
                yield ref
        else:
            yield (sample_name(data), data)

def get_id(internal_id, sample):
    res = internal_id.split("_", 2)[1]
    return sample + "-" + res

id_re = re.compile("\\d+")
split_format = re.compile("^([\w.-]+)_\(\d+_\d+\)$")

def extract_id(name):
    bin_id = None
    params = name.split("-", 1)
    if len(params) > 1:
        bin_id = int(id_re.findall(params[0])[0])
        name = params[1]
    contig_id = int(id_re.findall(name)[0])
    if bin_id is None:
        return contig_id
    else:
        return (bin_id, contig_id)

def load_annotation(file, normalize=True):
    res = dict()
    sample, _ = os.path.splitext(os.path.basename(file))
    with open(file) as input:
        for line in input:
            info = line.split("\t")
            id = get_id(info[0], sample) if normalize else info[0]
            bins = info[1].split()
            if id in res:
                res[id].update(bins)
            else:
                res[id] = set(bins)
    return res

def contig_length(name):
    # Length of contig split
    split = re.search("\((\d+)_(\d+)\)", name)
    if split:
        return int(split.group(2)) - int(split.group(1))
    #Default format
    else:
        return int(name.split("_")[3])

