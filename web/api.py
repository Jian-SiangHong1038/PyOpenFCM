import datetime, sys, io, contextlib
from ..lib.fcm import FCM
from flask import Flask, session, redirect, url_for, escape, request

#create service application
app = Flask(__name__)

#app secret key - keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' #TODO - use generator or file

#html templates
index_template="template not loaded"
with open("templates/index.html","r",encoding="utf8") as f: index_template=f.read()
cs_index_template="template not loaded"
cs_maplogin_template="template not loaded"
cs_session_template="template not loaded"
cs_missing_template="template not loaded"
with open("templates/cs_index.html","r",encoding="utf8") as f: cs_index_template=f.read()
with open("templates/cs_maplogin.html","r",encoding="utf8") as f: cs_maplogin_template=f.read()
with open("templates/cs_session.html","r",encoding="utf8") as f: cs_session_template=f.read()
with open("templates/cs_missing.html","r",encoding="utf8") as f: cs_missing_template=f.read()
ss_index_template="template not loaded"
ss_maplogin_template="template not loaded"
ss_session_template="template not loaded"
ss_missing_template="template not loaded"
with open("templates/ss_index.html","r",encoding="utf8") as f: ss_index_template=f.read()
with open("templates/ss_maplogin.html","r",encoding="utf8") as f: ss_maplogin_template=f.read()
with open("templates/ss_session.html","r",encoding="utf8") as f: ss_session_template=f.read()
with open("templates/ss_missing.html","r",encoding="utf8") as f: ss_missing_template=f.read()

#service index
@app.route("/")
def index():
    return index_template

#-CLIENT-SIDE-API-----------------------------------------------#
    
@app.route('/cs/')
def cs_index():
    if 'client_name' in session:
        return cs_index_template.replace("{R}",session['client_name'])
    return redirect(url_for('cs_login'))

@app.route('/cs_login/', methods=['GET', 'POST'])
def cs_login():
    if request.method == 'POST':
        map=FCM()
        map.name=request.form['mapname']
        session['client_map'] = map.serialize()
        session['client_name'] = map.name
        return redirect(url_for('cs_index')+session['client_name'])
    return cs_maplogin_template

@app.route('/cs_logout/')
def cs_logout():
    # remove the map from the session if it's there
    session.pop('client_map', None)
    session.pop('client_name', None)
    return redirect(url_for('cs_index'))

@app.route('/cs/<mapname>/')
def cs_session(mapname):
    if 'client_name' in session and session['client_name']==mapname:
        return cs_session_template.replace("{R}",session['client_name'])
    if 'client_name' not in session:
        return redirect(url_for('cs_login'))
    return cs_missing_template.replace("{R1}",mapname).replace("{R2}",session['client_name'])

@app.route('/cs/<mapname>/execute/<command>/')
def cs_process(mapname,command):
    if 'client_name' in session and session['client_name']==mapname:
        #processing start time
        st=datetime.datetime.now()
        #secure command (no underlines)
        cmd=command.replace("_","")
        #create FCM object
        _map_=FCM(session['client_map'])
        #use FCM object in command
        cmd=cmd.replace(session['client_name'],"_map_")
        #execute secured command
        response=execute(_map_,cmd)
        response=response.replace("_map_",session['client_name'])
        #update client FCM cookie
        session['client_map']=_map_.serialize()
        #processing end time
        et=datetime.datetime.now()
        #processing duration (ms)
        dt=(et-st).total_seconds()*1000
        #generate response
        ret=">>> "+command+"\n"
        ret+="-------------------------------------\n"
        ret+=response
        ret+="-------------------------------------\n"
        ret+="Processed in "+str(dt)+"ms."
        ret="<pre>"+ret+"</pre>"
        return ret
    if 'client_name' not in session:
        return redirect(url_for('cs_login'))
    return cs_missing_template.replace("{R1}",mapname).replace("{R2}",session['client_name'])
    
@app.route('/cs/<mapname>/serialize/')
def cs_serialize(mapname):
    if 'client_name' in session and session['client_name']==mapname:
        _map_=FCM(session['client_map'])
        return _map_.serialize()
    if 'client_name' not in session:
        return redirect(url_for('cs_login'))
    return cs_missing_template.replace("{R1}",mapname).replace("{R2}",session['client_name'])

#-SERVER-SIDE-API-----------------------------------------------#

ss_maps={}
    
@app.route('/ss/', methods=['GET', 'POST'])
def ss_index():
    if request.method == 'POST':
        #work with existing FCM
        if 'name' in request.form:
            mapname = request.form['name']
            if mapname in ss_maps:
                return redirect(url_for('ss_index')+mapname)
            return ss_missing_template.replace("{R}",mapname)
        #create new FCM
        if 'logname' in request.form:
            mapname = request.form['logname']
            return redirect(url_for('ss_index')+mapname+"/login/")
        #delete existing FCM
        if 'remname' in request.form:
            mapname = request.form['remname']
            return redirect(url_for('ss_index')+mapname+"/logout/")
        #get FCM as JSON
        if 'getname' in request.form:
            mapname = request.form['getname']
            return redirect(url_for('ss_index')+mapname+"/serialize/")
    return ss_index_template

@app.route('/ss/<mapname>/login/', methods=['GET', 'POST'])
def ss_login(mapname):
    if request.method == 'POST':
        ss_maps[mapname]=FCM()
        ss_maps[mapname].name=mapname
        return redirect(url_for('ss_index')+mapname)
    if mapname not in ss_maps:
        ss_maps[mapname]=FCM()
        ss_maps[mapname].name=mapname
        return redirect(url_for('ss_index')+mapname)
    return ss_maplogin_template.replace("{R}",mapname)
        
@app.route('/ss/<mapname>/logout/')
def ss_logout(mapname):
    # remove the map from the list if it's there
    ss_maps.pop(mapname, None)
    return redirect(url_for('ss_index'))
    
@app.route('/ss/<mapname>/')
def ss_session(mapname):
    print("session")
    if mapname in ss_maps:
        return ss_session_template.replace("{R}",mapname)
    return ss_missing_template.replace("{R}",mapname)
    
@app.route('/ss/<mapname>/execute/<command>/')
def ss_process(mapname,command):
    if mapname in ss_maps:
        #processing start time
        st=datetime.datetime.now()
        #secure command (no underlines)
        cmd=command.replace("_","")
        #get FCM object
        _map_=ss_maps[mapname]
        #use FCM object in command
        cmd=cmd.replace(mapname,"_map_")
        #execute secured command
        response=execute(_map_,cmd)
        response=response.replace("_map_",mapname)
        #processing end time
        et=datetime.datetime.now()
        #processing duration (ms)
        dt=(et-st).total_seconds()*1000
        #generate response
        ret=">>> "+command+"\n"
        ret+="-------------------------------------\n"
        ret+=response
        ret+="-------------------------------------\n"
        ret+="Processed in "+str(dt)+"ms."
        ret="<pre>"+ret+"</pre>"
        return ret
    return ss_missing_template.replace("{R}",mapname)
    
@app.route('/ss/<mapname>/serialize/')
def ss_serialize(mapname):
    if mapname in ss_maps:
        return ss_maps[mapname].serialize()
    return ss_missing_template.replace("{R}",mapname)

#-AUXILIARY----------------------------------------------------#

#execute command (with specified map)
def execute(_map_,cmd):
    with stdoutIO() as s:
        #catch and return errors when not debugging
        if not app.debug:
            try:
                try:
                    response=str(eval(cmd,{'__builtins__': {"print":print},"dir":dir,"help":help},{"_map_":_map_}))+"\n"
                    if response=="None\n": response=s.getvalue()
                except SyntaxError:
                    exec(cmd,{'__builtins__': {"print":print},"dir":dir,"help":help},{"_map_":_map_})
                    response=s.getvalue()
                if response=="":
                    response=str(_map_)+"\n"
            except BaseException as error:
                print("Error:", error)
                response=s.getvalue()
        #do not catch errors when debugging since Flask will show full error traceback
        else:
            try:
                response=str(eval(cmd,{'__builtins__': {"print":print},"dir":dir,"help":help},{"_map_":_map_}))+"\n"
                if response=="None\n": response=s.getvalue()
            except SyntaxError:
                exec(cmd,{'__builtins__': {"print":print},"dir":dir,"help":help},{"_map_":_map_})
                response=s.getvalue()
            if response=="":
                response=str(_map_)+"\n"
    return response

#url parser
def getmapncmd(s):
    nonchar=-1
    for i in range(len(s)):
        if not s[i].isalnum():
            nonchar=i
            break
    if nonchar != -1:
        name=s[0:nonchar]
        cmd=s[nonchar:]
    else:
        name=s
        cmd=""
    return name, cmd
    
#web output context manager
@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = io.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

#--------------------------------------------------------------#

# entry point for the application
if __name__ == "__main__":
    app.run(host='127.0.0.1',debug=True)
