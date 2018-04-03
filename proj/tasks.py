from celery import Celery
import os
import glob
import zipfile
import pdb
from os.path import basename
app = Celery('tasks', backend='rpc://', broker='amqp://localhost')

@app.task
def add(x, y):
    return x + y


@app.task
def run_helper_xenoGI_2(XENO_GI_DIRECTORY, data_filepath):
    """ 
    Runs the xenoGI package on the uploaded tree file and genbank file.
    - Sets up the starter file package
    - Runs sequence of command to get xenoGI output
    @param file_directory: inner directory of the files 
    """


    code_pipeline = ['parseGenbank.py', 'runBlast.py', 'calcScores.py', 'xenoGI.py',
                     'printAnalysis.py']
    param_fn = 'params.py'

    # copy the starter .txt files to current directory
    os.chdir(data_filepath) 
    for step in code_pipeline:
        # create the python command to run
        xeno_gi_step = os.path.join(XENO_GI_DIRECTORY, step)
        python_step = "python3 " + xeno_gi_step + " " + param_fn
        os.system(python_step) 
     
    # writing the bed files too  
    make_beds = os.path.join(XENO_GI_DIRECTORY, "misc", "createIslandBed.py")
    BED_PARAM = str(100)
    python_step_bedfiles = "python3 " +  make_beds + " " + param_fn + " " + BED_PARAM 
    os.system(python_step_bedfiles) 
    print("pre-print") 

    output_files = glob.glob('*.out')
    bed_files = glob.glob('bed/*')

    os.chdir(data_filepath) 
    print(data_filepath)
    ZIP_FN= "xenogi_output.zip"
    os.system("chmod ugo+r " + ZIP_FN)
 
    file_list = map (lambda u: os.path.join(data_filepath, u), output_files)
    bfs = map (lambda u: os.path.join(data_filepath, u), bed_files)
    with zipfile.ZipFile(ZIP_FN, 'w') as myzip:
        for fn in file_list:
           myzip.write(fn, basename(fn))
        for bf in bfs:
            print(bf)
            print(basename(bf))
            subfolder = "bed/" + basename(bf) 
            myzip.write(bf, subfolder) 
        myzip.close()

"""
class OutputFilesService:
    def __init__(self, directory,file_list, bed_files):
        self.directory = directory 
        self.zip_fn = 'xenogi_output.zip'
        self.files = file_list
        self.bed= bed_files 


    def create_zip(self):
        ''' 
        Write a zipfile with the given list
        @param filepath: directory of output files 
        @param file_list: list of the given files, i.e. fam.out, islands.out
        '''
        print("Creating the zipfile is called")
        file_list = self.files
        directory = self.directory
        bfs = self.bed
        #give absolute paths for the file_list
        file_list = map (lambda u: os.path.join(directory, u), file_list)
      
        bfs = map (lambda u: os.path.join(directory, u), bfs)
        with zipfile.ZipFile(self.zip_fn, 'w') as myzip:
            for fn in file_list: 
                myzip.write(fn, basename(fn))
            for bf in bfs:
                subfolder = "bed/" + basename(bf) 
                myzip.write(bf, subfolder)
        myzip.close()
"""
