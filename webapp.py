from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
from datetime import datetime
#from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template
import pymongo
import pprint
import os
from markupsafe import Markup


# This code originally from https://github.com/lepture/flask-oauthlib/blob/master/example/github.py
# Edited by P. Conrad for SPIS 2016 to add getting Client Id and Secret from
# environment variables, so that this will work on Heroku.
# Edited by S. Adams for Designing Software for the Web to add comments and remove flash messaging
# Edited by pierce for his project

app = Flask(__name__)

app.debug = False #Change this to False for production
#os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information
connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]
client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['ForumPro'] #1. put the name of your collection in the quotes
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)


#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary 
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    is_logged_in = 'github_token' in session #this will be true if the token is in the session and false otherwise
    return {"logged_in":is_logged_in}

@app.route("/", methods=["GET"])
def home():
    ForumPro = collection.find().sort("date", pymongo.DESCENDING) 
    
    return render_template('page3.html', ForumPro=ForumPro)
     
# Route to display the post creation form
@app.route("/NewPost", methods=["GET", "POST"])
def post():
    #if 'github_token' not in session:
        # Redirect to login page if user is not logged in
        #return redirect(url_for('login'))
    
    if request.method == "POST":
        # Get data from the form
        title = request.form.get("title")
        content = request.form.get("content")
        author = request.form.get("author")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        # Get the author's GitHub username
        author = session['user_data']['login']
        
        # Automatically set the current date
        date = datetime.now().strftime("%Y-%m-%d %I:%M %p")  # Format as YYYY-MM-DD II:MM:SS AM or PM

        # Create the post document
        new_post = {
            "title": title,
            "content": content,
            "author": author,
            "date": date,
            "latitude": latitude,
            "longitude": longitude
        }

        # Insert the new post into MongoDB
        collection.insert_one(new_post)

        # Redirect back to the homepage or another page after posting
        #return redirect(url_for("Home"))

    return render_template('home.html')  # Display the form to create a post

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    return render_template('message.html', message='You were logged out')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            message='You were successfully logged in as ' + session['user_data']['login'] + '. ' + Markup("<a href='http://127.0.0.1:5000/'>Click here to go to homepage!</a>")
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('message.html', message=message)


@app.route('/Search', methods=["GET", "POST"])
def renderPage1():
    if 'user_data' in session:
        user_data_pprint = pprint.pformat(session['user_data'])#format the user data nicely
    else:
        user_data_pprint = '';
    query = request.form.get('query', '')  # Get search query from the form
    posts = []

    if query:
        # Perform a text search on the 'title' and 'content' fields
        posts = collection.find({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},  # case-insensitive match
                {"content": {"$regex": query, "$options": "i"}}
            ]
        })

    return render_template('page1.html', posts=posts, query=query)

@app.route('/Map')
def renderPage2():
    if "user_data" in session:
         dataPoints1 = pprint.pformat(session['user_data']["bio"])
         dataPoints2 = pprint.pformat(session['user_data']["blog"])
         dataPoints3 = pprint.pformat(session['user_data']["company"])
    else:
        dataPoints1="n/a"
        dataPoints2="n/a"
        dataPoints3="n/a"

    return render_template('page2.html', dataPoints1=dataPoints1, dataPoints2=dataPoints2, dataPoints3=dataPoints3)

@app.route('/googleb4c3aeedcc2dd103.html')
def render_google_verification():
    return render_template('googleb4c3aeedcc2dd103.html')

#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run()
