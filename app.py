from flask import Flask, request,jsonify,make_response,Response
from flask_restplus import Api, Resource, fields, reqparse
from werkzeug.middleware.proxy_fix import ProxyFix
from dbconnection import connection
from datetime import timedelta
from flask_cors import CORS
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token,JWTManager,set_access_cookies
import enum,json


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config["JWT_SECRET_KEY"] = "dranzer" 
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
app.config["JWT_TOKEN_LOCATION"] = [ "cookies"]
app.config["JWT_COOKIE_SECURE"] = False

jwt = JWTManager(app)


api = Api(app, version='1.0', title='TodoMVC API',
    description='A simple TodoMVC API',
)
CORS(app)


cursor = connection.cursor(buffered=True)

ns = api.namespace('todos', description='TODO operations')
nsAuth = api.namespace('auth',description = 'Authorization operations')



class EnumStatus(enum.Enum):
    NotStarted = 'Not Started'
    InProgress = 'In Progress'
    Finished = 'Finished'

todo = api.model('Todo', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'task': fields.String(required=True, description='The task details'),
    'dueby': fields.Date(required=True,description="DateFormat: 'YYYY-mm-dd' The last date to complete the task",default=None),
    'status': fields.String(enum=[x.value for x in EnumStatus],description="The status of the task",default=EnumStatus.NotStarted.value)
})

user = api.model('User', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'name': fields.String(required=True, description='The name of the user'),
    'username': fields.String(required=True, description='The user_name of the user'),
    'email': fields.String(required=True, description='The email of the user'),
    'password': fields.String(required=True, description='The encrypted password of the user'),
    'role': fields.Integer(required=True, description='The role of the user (0-User) (1-Admin)'),
})

login = api.model('Login',{
    'email': fields.String(required=True, description='The email of the user'),
    'password': fields.String(required=True, description='The  password entered by the user')
})


class TodoDAO(object):
    def __init__(self):
        self.todos = []
        self.load()

    def load(self):
        cursor.execute("SELECT * FROM todo")
        row_headers = [x[0] for x in cursor.description]
        result = cursor.fetchall()
        for x in result:
            self.todos.append(dict(zip(row_headers,x)))

    def get(self, id):
        for todo in self.todos:
            if todo['id'] == id:
                return todo
        api.abort(404, "Todo {} doesn't exist".format(id))

    def create(self, data):
        todo = data
        if 'status' not in data:
            todo['status'] = EnumStatus.NotStarted.value
        
        
        self.todos.append(todo)
        
        columns = ', '.join("`" + str(x).replace('/', '_') + "`" for x in todo.keys())
        values = ', '.join("'" + str(x).replace('/', '_') + "'" for x in todo.values())
        sql = "INSERT INTO %s ( %s ) VALUES ( %s );" % ("todo", columns, values)
        cursor.execute(sql)
        connection.commit()
        todo['id'] = cursor.lastrowid
        
        return todo

    def update(self, id, data):
        todo = self.get(id)
        todo.update(data)

        temp = dict(todo)
        temp.pop('id')
        sql = 'UPDATE {} SET {} WHERE id={}'.format('todo',', '.join('{}=%s'.format(k) for k in temp),id)

        cursor.execute(sql,list(temp.values()))
        connection.commit()
        return todo

    def delete(self, id):
        todo = self.get(id)
        self.todos.remove(todo)
        cursor.execute("DELETE FROM {} WHERE id={}".format("todo",id))
        connection.commit()


    """0 - Not Started , 1 - InProgress, 2-Finished"""
    def changeStatus(self,id,code):
       
        todo = self.get(id)
        data = dict(todo)
        if code == 0:
            data['status'] = EnumStatus.NotStarted.value
        elif code == 1:
            data['status'] = EnumStatus.InProgress.value
        elif code == 2:
            data['status'] = EnumStatus.Finished.value  
       
        todo.update(data)
        sql = 'UPDATE {} SET status="{}" WHERE id={}'.format('todo',data['status'],id)
        cursor.execute(sql)
        connection.commit()
    

        return todo


DAO = TodoDAO()




@ns.route('/')
class TodoList(Resource):
    '''Shows a list of all todos, and lets you POST to add new tasks'''
    @ns.doc('list_todos')
    @ns.marshal_list_with(todo)
    def get(self):
        '''List all tasks'''
        return DAO.todos

    @ns.doc('create_todo')
    @ns.expect(todo)
    @ns.marshal_with(todo, code=201)
    def post(self):
        '''Create a new task'''
        return DAO.create(api.payload), 201


@ns.route('/<int:id>')
@ns.response(404, 'Todo not found')
@ns.param('id', 'The task identifier')
class Todo(Resource):
    '''Show a single todo item and lets you delete them'''
    @ns.doc('get_todo')
    @ns.marshal_with(todo)
    def get(self, id):
        '''Fetch a given resource'''
        return DAO.get(id)


    @ns.doc('delete_todo')
    @ns.response(204, 'Todo deleted')
    def delete(self, id):
        '''Delete a task given its identifier'''
        DAO.delete(id)
        return '', 204


    @ns.expect(todo)
    @ns.marshal_with(todo)
    def put(self, id):
        '''Update a task given its identifier'''
        return DAO.update(id, api.payload)


@ns.route('/status/<int:id>/<int:statuscode>')
@ns.response(404,"Invalid status code")
@ns.param('id','The id of the task whose status need to be changed')
@ns.param('statuscode','The code of a status which will replace the existing status')
class StatusChange(Resource):
    '''Change the status of the given task'''
    
    @ns.marshal_with(todo)
    def put(self,id,statuscode):
        '''Change the status of the task given its identifier'''
        return DAO.changeStatus(id,statuscode)

@ns.route('/finished')
@ns.response(404,"Unable to access finished tasks")
class FinishedTasks(Resource):
    '''Get all the finished tasks'''

    @ns.marshal_list_with(todo)
    def get(self):
        '''Get all the finished tasks'''
        finished_todo = []
        for todo in DAO.todos:
            if todo['status'] == EnumStatus.Finished.value:
                finished_todo.append(todo)
        return finished_todo


        

@ns.route('/overdue')
@ns.response(404,"This returns the overdue tasks")
class OverDueTasks(Resource):
    '''Get all the overdue tasks'''

    @ns.marshal_list_with(todo)
    def get(self):
        '''Get all the overdue tasks'''
        overdue = []
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM todo WHERE dueby<now()")
        row_headers = [x[0] for x in cursor.description]
        result = cursor.fetchall()
        for x in result:
            overdue.append(dict(zip(row_headers,x)))
        return overdue


parser = reqparse.RequestParser()
rparser = ns.parser()
rparser.add_argument('due_date',required=True)

@ns.route('/due')
@ns.expect(rparser)
@ns.response(404,"The tasks which due ends during a particular date")
class DueAtParticularDate(Resource):
    '''Get the tasks that's due on a particular data'''
    @ns.marshal_list_with(todo)
    def get(self):
        '''Get the tasks due on a particular date'''
        due_date =[]
        QueryDate =  rparser.parse_args()
        QueryDateValue = QueryDate["due_date"]
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM todo WHERE DATE(dueby)='{}'".format(QueryDateValue))

        row_headers = [x[0] for x in cursor.description]
        result = cursor.fetchall()
        for x in result:
            due_date.append(dict(zip(row_headers,x)))
        return due_date



class UserDAO(object):
    def create(self,data):
        user = data
        check_email_query = "SELECT email FROM user WHERE email=\'{}\'".format(user['email'])
        cursor.execute(check_email_query)
        result = cursor.fetchone()
        if result:
            if user['email'] in result:
                return {"error" : "email already exists"},422

        columns = ', '.join("`" + str(x).replace('/', '_') + "`" for x in user.keys())
        values = ', '.join("'" + str(x).replace('/', '_') + "'" for x in user.values())
        sql = "INSERT INTO %s ( %s ) VALUES ( %s );" % ("user", columns, values)
        cursor.execute(sql)
        connection.commit()
        user['id'] = cursor.lastrowid
        
        return user

    def signIn(self,data):
        email = data['email']
        password = data['password']
        get_email_password_query = "SELECT email,password,role FROM user WHERE email=\'{}\'".format(email)
        cursor.execute(get_email_password_query)
        result = cursor.fetchone()
        role = result[2]
        if result:
            if check_password_hash(result[1],password):
                expires = timedelta(hours=24)
                access_token = create_access_token(identity=str(email),expires_delta=expires)
                response = {"token":access_token,"message" : "login success","role" : role }
                return response,200
        else:
            return {"error" : "login failed"},422




UDAO = UserDAO()

@nsAuth.route('/signup')
@ns.response(404,"singup failed")
class Signup(Resource):
    '''Signup the user'''
    @ns.doc('create_user')
    @ns.expect(user)
    def post(self):
        '''Create a new user'''
        return UDAO.create(api.payload), 201

@nsAuth.route('/signin')
@ns.response(404,"singin failed") 
class Signin(Resource):
    '''Signin the user'''
    @ns.doc('login_user')
    @ns.expect(login)
    def post(self):
        '''Signin a existing user'''
        return UDAO.signIn(api.payload), 201



if __name__ == '__main__':
    app.run(debug=True)