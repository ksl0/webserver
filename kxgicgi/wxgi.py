#!/usr/bin/python3
from flask import Flask, request, render_template, send_from_directory, Markup, redirect, url_for
from werkzeug import secure_filename
from werkzeug.debug import DebuggedApplication
import os, datetime, sys
from os.path import basename
from wsgiref.handlers import CGIHandler
import cgitb
import zipfile
import io
import glob
import time


# for xenoGI code
sys.path.append(os.path.join(sys.path[0],'../xenoGI/'))
import parameters

sys.path.append(os.path.join(sys.path[0],'../proj/'))
from tasks import add
from tasks import run_helper_xenoGI_2 
cgitb.enable()

app = Flask(__name__)

PERSON = 'kxgicgi'
USER_DIR = 'katie'
ALLOWED_EXTENSIONS = set(['tre', 'newick', 'gbff'])

BASE_DIRECTORY= os.path.join('/data/bushlab/htrans/', USER_DIR)
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
    return render_template('form.html', person=PERSON, page='upload')

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
            os.system("chmod ugo+rwx " + thisFolderName)
            os.chdir(thisFolderName)
            treeFile.save(os.path.join(app.config['WORK_DIRECTORY'], thisFolderName, TREE_FN))

 
            #rewrite the parameters file from the xenoGI/examples/params.py
            paramDefaultFile = os.path.join(XENO_GI_DIRECTORY, "example", "params.py")
            thisFolderPath = os.path.join(WORK_DIRECTORY, thisFolderName)
            os.system("cp "+  paramDefaultFile + " " +  ".")
            paramFN = os.path.join(thisFolderPath, "params.py")
            paramD = parameters.loadParametersD(paramFN)
            paramD['fileNameMapFN'] = None  # we assume the user does not have a human to gbff file mapping

            #if you want to add another parameter
            # then add additional line to form, following "rootFocal"
            # 1) update template/forms.html
            # 2) copy requst.forms[<parameter_name>]
            # 3) overwrite the paramD (loaded file from xenoGI/example/params.py) 
            rootFCUserInput= request.form['rootFocal']  # copy this line
            paramD['rootFocalClade'] = rootFCUserInput  # copy this line too - changing the value
            writeParamFile(paramD, paramFN) #rewrites paramFN

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

                 
                os.system("chmod ugo+rwx " + thisFolderName + "/ncbi/*")
                os.system("chmod ugo+rwx " + thisFolderName + "/*")
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
    celery_result = run_helper_xenoGI_2.delay(XENO_GI_DIRECTORY, current_wd)
    #output_files, bed_files = celery_result.get()    
    #writeHelper(current_wd, output_files, bed_files) 
    #return return_files(tree_fn)

    url = os.path.join(WEB_URL, 'return-files',  tree_fn) + '.zip'
    return render_template("program_inprogress.html", url = url)

@app.route('/landing/<tree_fn>', methods= ["GET", "POST"])
def intermediate(tree_fn): 
    """
    Creates a intermediate page w/ a run button, the submitted files list, and the download link
    """
    url = os.path.join(WEB_URL, 'return-files',  tree_fn) + '.zip'
    return render_template("landing.html", person=PERSON, tree_fn = tree_fn, url=url)

def writeParamFile(param_dict, paramFilename):
    with open(paramFilename, 'w') as fid:
        for key in param_dict:
            # check if value is a string file or not
            # if it is, we need double quotes around it
            if (isinstance(param_dict[key], str)):
                line = '%s = \"%s\" \n' % (key, param_dict[key])
            else:
                line = "%s = %s \n" % (key, param_dict[key])
            fid.write(line)
    fid.close() 

if __name__ == '__main__':
    app.debug = True # change to false once things are running.
    application = DebuggedApplication(app, True)
    CGIHandler().run(application)

