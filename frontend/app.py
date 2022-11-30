from flask import Flask,render_template,url_for,request,redirect,make_response
import requests
import json
from werkzeug.security import generate_password_hash

app = Flask(__name__)
headers = {'Content-Type': 'application/json'}
token = ""
role = 0


@app.route('/signup',methods=['GET','POST'])
def signup():
    
    isPasswordMatched = True
    isEmailUnique = True
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']   
        email = request.form['email']
        password = request.form['password']
        cpassword = request.form['cpassword']

        if password!=cpassword:
            isPasswordMatched = False
            return render_template("signup.html",isPasswordMatched=isPasswordMatched,isEmailUnique = isEmailUnique)
        
        password = generate_password_hash(password,"sha256")

        data = {
            "name" : name,
            "username" : username,
            "email": email,
            "password": password,
            "role": 0
        }

        data = json.dumps(data)

        try:
            createUser = requests.post("http://localhost:5000/auth/signup",data=data,headers=headers)
            # print(createUser.json())
            if createUser:
                if "error" in createUser.json()[0] or 422 in createUser.json():
                    isEmailUnique = False
                    return render_template("signup.html",isPasswordMatched=isPasswordMatched,isEmailUnique = isEmailUnique)
            else: 
                redirect('/signin')
        except:
            return "Sorry for the inconvenience. There was an issue adding your task"
    else:
        return render_template("signup.html",isPasswordMatched = isPasswordMatched,isEmailUnique=isEmailUnique)

   

@app.route('/signin',methods=['GET','POST'])
def signin():
    isSignedIn = True
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']   
        data = {
            "email" : email,
            "password" : password,
        }
        data = json.dumps(data)
        try:
            siginInResults = requests.post("http://localhost:5000/auth/signin",data=data,headers=headers)
            siginInResults = siginInResults.json()
            if 200 in siginInResults or "token" in siginInResults[0]:
                # print(siginInResults[0]['token'])
                token = siginInResults[0]['token']
                role_val = siginInResults[0]['role']
                role = role_val
                getAllTasksResponse = requests.get("http://localhost:5000/todos/",headers=headers)
                return render_template('index.html',tasks=getAllTasksResponse.json(),role = role)
        except:
            isSignedIn = False
            return render_template('signin.html',isSignedIn=isSignedIn)
    else:
        return render_template("signin.html",isSignedIn=isSignedIn)


@app.route('/',methods=['POST','GET'])
def home():
    if request.method == 'POST':
        task = request.form['task']
        dueby = request.form['dueby']   
        status = request.form['status']
        data = {
            "task" : task,
            "dueby" : dueby,
            "status" : status
        }
        data = json.dumps(data)
        
        try:
            createTask = requests.post("http://localhost:5000/todos/",data=data,headers=headers)
            return redirect("/")
        except:
            return "There was an issue adding your task"

    else:       
        getAllTasksResponse = requests.get("http://localhost:5000/todos/",headers=headers)
        # print(getAllTasksResponse.json())
        return render_template("index.html",tasks=getAllTasksResponse.json())


@app.route('/delete/<int:id>')
def delete(id):
    pheaders = {'Content-Type': 'application/json','Authorization' : 'Bearer {}'.format(token)}
    
    try:
        deleteTaskResponse = requests.delete("http://localhost:5000/todos/{}".format(id),headers=pheaders)

        getAllTasksResponse = requests.get("http://localhost:5000/todos/",headers=headers)
        # print(getAllTasksResponse.json())
        return render_template("index.html",tasks=getAllTasksResponse.json())
    except:
        return "There was a problem deleting the task"


@app.route('/update/<int:id>',methods=['GET','POST'])
def update(id):
    pheaders = {'Content-Type': 'application/json','Authorization' : 'Bearer {}'.format(token)}
    task = requests.get("http://localhost:5000/todos/{}".format(id))
    task = task.json()
    
    if request.method == 'POST':
        task = request.form['task']
        dueby = request.form['dueby']   
        status = request.form['status']
        data = {
            "task" : task,
            "dueby" : dueby,
            "status" : status
        }
        data = json.dumps(data)
    
        try:
            requests.put("http://localhost:5000/todos/{}".format(id),data=data,headers=pheaders)
            getAllTasksResponse = requests.get("http://localhost:5000/todos/",headers=headers)
            return render_template("index.html",tasks=getAllTasksResponse.json(),role=role)
        except Exception as e:
            return "There was an issue updating your task {}".format(e)
    else:
        return render_template('update.html',task=task)






   


        
            
       
        


if __name__=='__main__':
    app.run(debug=True,port=5001)