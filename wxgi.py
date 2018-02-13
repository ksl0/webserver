#!/usr/bin/python3
from flask import Flask, request, render_template, send_from_directory, Markup
from werkzeug import secure_filename
from werkzeug.debug import DebuggedApplication
import os, datetime
from wsgiref.handlers import CGIHandler
import cgitb
cgitb.enable()

app = Flask(__name__)

ALLOWED_EXTENSIONS = set(['tre', 'newick', 'gbff'])

BASE_DIRECTORY= '/data/bushlab/htrans/katie/kxgicgi/'
XENO_GI_DIRECTORY = '/data/bushlab/htrans/katie/xenoGI/'
WORK_DIRECTORY = '/data/bushlab/htrans/katie/xgiBox/'
app.config['WORK_DIRECTORY'] = WORK_DIRECTORY

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def hello_world():
    return("Flask is working.\n")

@app.route('/form')
def form():
    """Returns the form page"""
    return render_template('form.html', page='upload')


@app.route('/run', methods = ['POST'])
def runXenoGI(carousel = None):
    """ Runs xenoGI."""
    MAX_GB_FC = 20 
    MIN_GB_FC = 3
    TREE_FN = "example.tre"
    if request.method == 'POST':

        treeFile = request.files['newick']

        if treeFile and allowed_file(treeFile.filename):
            treeFileName = secure_filename(treeFile.filename)
            now=datetime.datetime.now()
            thisFolderName = treeFileName + '-' + str(now.timestamp()).split('.')[0]# timestamp to make unique
            #this working directory is the user's "working directory"
            current_wd = os.path.join(app.config['WORK_DIRECTORY'], thisFolderName)

            os.chdir(WORK_DIRECTORY)
            os.system("mkdir "+thisFolderName)
            os.chdir(thisFolderName)
            treeFile.save(os.path.join(app.config['WORK_DIRECTORY'], thisFolderName, TREE_FN))

            #copy starter files over
            starter_files = os.path.join(BASE_DIRECTORY, "STARTER_FILES/*")
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
                steps = run_helper_xenoGI(current_wd)
                return "Done.  &#x2603; "
        else: #refer user back to the documentation 
            return render_template("documentation.html")


def run_helper_xenoGI(data_filepath):
    """ 
    Runs the xenoGI package on the uploaded tree file and genbank file.
    - Sets up the starter file package
    - Runs sequence of command to get xenoGI output
    @param file_directory: inner directory of the files 
    """
    code_pipeline = ['parseGenbank.py', 'runBlast.py', 'calcScores.py', 'xenoGI.py']
    param_fn = 'params.py'
   
    

    # copy the starter .txt files to current directory
    os.chdir(data_filepath) 
    python_steps = []

    python_steps.append(data_filepath)
    for step in code_pipeline:
        # create the python command to run
        xeno_gi_step = os.path.join(XENO_GI_DIRECTORY, step)
        python_step = "python3 " + xeno_gi_step + " " + param_fn
        python_steps.append(python_step)
        os.system(python_step)
    return python_steps
   
if __name__ == '__main__':
    app.debug = True # change to false once things are running.
    application = DebuggedApplication(app, True)
    CGIHandler().run(application)


    
