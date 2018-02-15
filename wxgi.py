#!/usr/bin/python3
from flask import Flask, request, render_template, send_from_directory, Markup, redirect, url_for
from werkzeug import secure_filename
from werkzeug.debug import DebuggedApplication
import os, datetime
from os.path import basename
from wsgiref.handlers import CGIHandler
import cgitb
import zipfile
import io
import glob

cgitb.enable()


app = Flask(__name__)

PERSON = 'kxgicgi'

ALLOWED_EXTENSIONS = set(['tre', 'newick', 'gbff'])

BASE_DIRECTORY= '/data/bushlab/htrans/katie/'
CGI_DIRECTORY= os.path.join(BASE_DIRECTORY, PERSON)
XENO_GI_DIRECTORY = os.path.join(BASE_DIRECTORY, 'xenoGI')
WORK_DIRECTORY = os.path.join(BASE_DIRECTORY, 'xgiBox')
app.config['WORK_DIRECTORY'] = WORK_DIRECTORY

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

WEB_URL= 'http://siva.cs.hmc.edu/'+  PERSON + '/wxgi.py/'


@app.route('/')
def hello_world():
    return("Flask is working.\n")

@app.route('/form')
def form():
    """Returns the form page"""
    return render_template('form.html', page='upload')

@app.route('/return-files/<zpf>.zip')
def return_files(zpf):
    sub_directory = os.path.join(WORK_DIRECTORY, zpf)
    try:
       return send_from_directory(sub_directory, "xenogi_output.zip")
    except Exception as e:
        return "zipfile not ready, please wait for the computation to finish " + str(e) 


@app.route('/upload_files', methods=["GET", "POST"])
def upload_files():
    """ Runs xenoGI."""
    MAX_GB_FC = 20 
    MIN_GB_FC = 3
    TREE_FN = "example.tre"
    if request.method == 'POST':

        treeFile = request.files['newick']

        if treeFile and allowed_file(treeFile.filename):
            treeFileName = secure_filename(treeFile.filename)
            treeFileName = treeFileName.split('.')[0]
            now=datetime.datetime.now()
            thisFolderName = treeFileName + '-' + str(now.timestamp()).split('.')[0]# timestamp to make unique
            #this working directory is the user's "working directory"
            current_wd = os.path.join(app.config['WORK_DIRECTORY'], thisFolderName)

            os.chdir(WORK_DIRECTORY)
            os.system("mkdir "+thisFolderName)
            os.chdir(thisFolderName)
            treeFile.save(os.path.join(app.config['WORK_DIRECTORY'], thisFolderName, TREE_FN))

            #copy starter files over
            starter_files = os.path.join(CGI_DIRECTORY, "STARTER_FILES/*")
            system_command ="cp "+  starter_files + " " + (os.path.join(app.config['WORK_DIRECTORY'], thisFolderName))
            os.system(system_command)      

            gbffFiles = request.files.getlist("gbff[]")

            if (len(gbffFiles) > MAX_GB_FC) or (len(gbffFiles) < MIN_GB_FC) :
                return render_template("documentation.html")
            else:  
                #make another directory *ncbi* for the gbfffiles
                GENBANK_FD= "ncbi" # this is set in params.py
                os.system("mkdir " + GENBANK_FD)
                for gbffFile in gbffFiles: 
                    if gbffFile and allowed_file(gbffFile.filename):
                        gbffFileName = secure_filename(gbffFile.filename)
                        gbffFile.save(os.path.join(app.config['WORK_DIRECTORY'], thisFolderName, GENBANK_FD, gbffFileName))              

 
            # go to the tree files  
            # work around to be in the right directory
            return redirect(url_for('intermediate', tree_fn = thisFolderName))
        else: #refer user back to the documentation 
            return render_template("documentation.html")
    else:
       return "nope"

@app.route('/run_program/<tree_fn>', methods = ['POST'])
def runXenoGI(tree_fn):
    """ Runs xenoGI file programs
        After running xenoGI, [return_files] will directly download the zipfiles
    """
    current_wd =  os.path.join(WORK_DIRECTORY, tree_fn)
    run_helper_xenoGI(current_wd)
    return return_files(tree_fn)

@app.route('/landing/<tree_fn>', methods= ["GET", "POST"])
def intermediate(tree_fn): 
    """
    Creates a intermediate page w/ a run button, the submitted files list, and the download link
    """
    url = os.path.join(WEB_URL, 'return-files',  tree_fn) + '.zip'
    return render_template("landing.html", tree_fn = tree_fn, url=url)
 
def run_helper_xenoGI(data_filepath):
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

    output_files = glob.glob('*.out')
    bed_files= (glob.glob("bed/*"))

    service = OutputFilesService(data_filepath, output_files, bed_files)
    service.create_zip()


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
    
  
if __name__ == '__main__':
    app.debug = True # change to false once things are running.
    application = DebuggedApplication(app, True)
    CGIHandler().run(application)


    
