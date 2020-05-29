from flask import Flask, render_template, request, session, url_for, redirect, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

#Initialize the app from Flask
app = Flask(__name__)
app.secret_key = "super secret key"  #added from github
IMAGES_DIR = os.path.join(os.getcwd(), "images")#added from github

#Configure MySQL
conn = pymysql.connect(host='127.0.0.1',
                       port = 3306,
                       user='root',
                       password='',
                       db='flaskdemo',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

#Define a route to hello function
@app.route('/')
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/click_to_follow')
def click_to_follow():
    return render_template('send_request.html')

@app.route('/click_to_see')
def click_to_see():
        #check that user is logged in
    username = session['username']
    cursor = conn.cursor();
    query = 'SELECT followerUsername FROM follow WHERE followeeUsername = %s AND acceptedfollow = 0'
    cursor.execute(query,(username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('see_request.html', user_list = data)

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    hash_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hash_password))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    hash_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person(username,password) VALUES(%s, %s)'
        cursor.execute(ins, (username, hash_password))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home')
@login_required 
def home():
    user = session['username']
    return render_template('home.html', username=user)

@app.route("/upload",methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")


@app.route("/image/<image_name>",methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR,image_name)
    if os.path.isfile(image_location):
        return send_file(image_location,mimetype="image/jpg")

@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files:
        username = session['username']
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        choose = request.form['choose']
        if (choose == "public"):
            query = "INSERT INTO photo (photoOwner,timestamp, filePath, allFollowers) VALUES (%s,%s,%s,1)"
            with conn.cursor() as cursor:
                cursor.execute(query, (username,time.strftime('%Y-%m-%d %H:%M:%S'), image_name))
            message = "Image has been successfully uploaded."
            return render_template("upload.html", message=message)
        else:
            query = "INSERT INTO photo (photoOwner,timestamp, filePath, allFollowers) VALUES (%s,%s,%s,0)"
            with conn.cursor() as cursor:
                cursor.execute(query, (username,time.strftime('%Y-%m-%d %H:%M:%S'), image_name))
            query2 = 'SELECT groupName FROM closefriendgroup WHERE groupOwner = %s '
            with conn.cursor() as cursor2:
                cursor2.execute(query2,username)
            data = cursor2.fetchall()
            return render_template("private.html", user_list=data)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)
    
@app.route("/tag_user", methods=["GET","POST"])
@login_required
def tag_user():
    username = session['username']
    query = "SELECT * FROM photo WHERE photoOwner = %s"
    with conn.cursor() as cursor:
        cursor.execute(query, (username))
    data = cursor.fetchall()
    if (not data):
        message = "You have 0 photo to tag other user, add photo to tag someone"
        return render_template("tag_when0photo.html", message = message)
    else:
        query2 = "SELECT photoID FROM photo WHERE photoOwner = %s"
        with conn.cursor() as cursor2:
            cursor2.execute(query2,username)
        data2 = cursor2.fetchall()
        query3 = "SELECT photoID, filePath FROM photo WHERE photoOwner = %s"
        with conn.cursor() as cursor3:
            cursor3.execute(query3,username)
        data3 = cursor3.fetchall()
        return render_template("tag.html",images=data,photo_list = data2,photo_list2 = data3)

@app.route("/tag_user2", methods=["GET","POST"])
@login_required
def tag_user2():
    username = session['username']
    friend = request.form['person_tagging']
    photoID = request.form['photoName']
    query = 'SELECT DISTINCT followeeUsername FROM follow NATURAL JOIN photo NATURAL JOIN person WHERE photoOwner = %s  AND followerUsername = %s AND allFollowers = 1 AND photoID = %s AND acceptedfollow =1 AND person.username = %s'
    with conn.cursor() as cursor:
        cursor.execute(query,(username,username,photoID,friend))
    data = cursor.fetchone()
    if (friend == username):
        query3 = "INSERT INTO tag VALUES (%s,%s,1)"
        with conn.cursor() as cursor3:
            cursor3.execute(query3,(friend,photoID))
        message = "tagging user complete"
        return render_template("tagResult.html",message = message)
    elif (data): #people who I accepted to follow me and the photo that's shared to all of my followers 
        query2 = "INSERT INTO tag VALUES (%s, %s, 0)"
        with conn.cursor() as cursor2:
            cursor2.execute(query2, (friend,photoID))
        message = "tag request sent"
        return render_template("tagResult.html",message = message)
    elif (data is None):
        query4 = 'SELECT DISTINCT username FROM belong NATURAL JOIN share NATURAL JOIN photo NATURAL JOIN follow WHERE photoOwner = %s AND username = %s AND allFollowers = 0 AND photoID = %s AND acceptedfollow = 1' ##Take a look
        with conn.cursor() as cursor4: 
            cursor4.execute(query4,(username, friend,photoID))
        data2 = cursor4.fetchone() #Picture is private and this selects the user that belongs to my close friend group 
        if (data2):
            query5 ="INSERT INTO tag VALUES (%s,%s,0)"
            with conn.cursor() as cursor5:
                cursor5.execute(query5, (friend,photoID))
            message = "tag request sent"
            return render_template("tagResult.html",message = message)
        else:
            error = "You are not able to tag him to that photo"
            return render_template("tagResult.html",error = error)

@app.route("/manage_tag", methods=["GET","POST"])
@login_required
def manage_tag():
    username = session['username']
    #if the current session username equals the username in the tag table, show the user the relevent data about the photo where the accepted Tag is 0 
    query = "SELECT photoID FROM photo NATURAL JOIN tag WHERE acceptedTag = 0 AND username = %s"
    with conn.cursor() as cursor:
        cursor.execute(query, (username))
    data = cursor.fetchall()
    query2 = "SELECT photoID, photoOwner, filePath FROM photo NATURAL JOIN tag WHERE acceptedTag = 0 AND username = %s"
    with conn.cursor() as cursor2:
        cursor2.execute(query2, (username))
    data2 = cursor2.fetchall()
    if (not data):
        message = "You have 0 tag request"
        return render_template("manageTagEmpty.html",message = message)
    else:
        return render_template("manageTag.html",user_list = data, user_list2 = data2)
    


    
@app.route("/manage_tag2", methods=["GET","POST"])
@login_required
def manage_tag2():
    username = session['username']
    photoID = request.args['tag_request']
    action = request.args['action']
    if (action == 'Accept'):
        query = "UPDATE tag SET acceptedTag = 1 WHERE username = %s AND photoID = %s"
        with conn.cursor() as cursor:
            cursor.execute(query, (username, photoID))
        message = "You are now tagged to that photo"
        return render_template("manageTagResult.html",message = message)
    elif (action == 'Decline'):
        query = "DELETE FROM tag WHERE username = %s AND photoID = %s"
        with conn.cursor() as cursor:
            cursor.execute(query, (username, photoID))
        message = "Your tag request has been removed" 
        return render_template("manageTagResult.html",message=message)
    else:
        message = "Ok, we'll remind you later" 
        return render_template("manageTagResult.html",message = message)
    
@app.route("/isPrivate", methods=["GET","POST"])
@login_required
def isPrivate():
    username = session['username']
    groupName = request.args["group_name"]
    photoID_query = 'SELECT photoID FROM photo WHERE allFollowers = 0 AND (photoID) NOT IN (SELECT photoID FROM share)'
    with conn.cursor() as cursor:
        cursor.execute(photoID_query)
    photo_ID_data = cursor.fetchone()
    photo_ID_num = photo_ID_data['photoID']
    query2 = "INSERT INTO share (groupName,groupOwner,photoID) VALUES (%s,%s,'%s')"
    with conn.cursor() as cursor2:
        cursor2.execute(query2, (groupName,username,photo_ID_num))
    message = "Image has been successfully uploaded."
    return render_template("upload.html", message=message)


@app.route("/create_cfg", methods=["GET","POST"])
@login_required
def create_cfg():
    return render_template("closefriendgroup.html")

@app.route("/create_cfg2", methods=["GET","POST"])
@login_required
def create_cfg2():
    username = session['username']
    cfg = request.form['cfg']
    check_query = 'SELECT * FROM closefriendgroup WHERE groupName = %s AND groupOwner = %s'
    with conn.cursor() as cursor:
        cursor.execute(check_query,(cfg,username))
    data = cursor.fetchone()
    if (data):
        error = "You already created this closefriendgroup"
        return render_template("closefriendgroup.html",error = error)
    else:
        query = 'INSERT INTO closefriendgroup VALUES (%s,%s)' 
        with conn.cursor() as cursor:
            cursor.execute(query,(cfg,username))
        message = "Successfully added"
        return render_template("closefriendgroup.html",message = message)

@app.route("/show_image", methods=["GET","POST"])
@login_required
def show_image():
    username = session['username']
    tagged_query = 'SELECT photoID FROM tag NATURAL JOIN photo WHERE username = %s AND acceptedTag = 1 AND (photoID) NOT IN (SELECT photoID FROM photo WHERE photoOwner = %s)'
    with conn.cursor() as cursor:
        cursor.execute(tagged_query, (username,username))
    data = cursor.fetchall()
    if (data): #person is tagged in the photo
        image_query = 'SELECT filePath FROM photo WHERE photoOwner = %s ORDER BY timestamp DESC' #used for image 
        with conn.cursor() as cursor:
            cursor.execute(image_query, (username))
        image_data = cursor.fetchall()
        tagImage_query = 'SELECT photoID,filePath FROM photo NATURAL JOIN tag WHERE tag.username = %s AND (photoID) NOT IN (SELECT photoID FROM photo WHERE photoOwner = %s)'
        with conn.cursor() as cursor2:
            cursor2.execute(tagImage_query, (username,username))
        tag_data = cursor2.fetchall()
        InfoQuery = 'SELECT photoID, photoOwner, caption FROM photo WHERE photoOwner = %s ORDER BY timestamp DESC'
        with conn.cursor() as cursor3:
            cursor3.execute(InfoQuery, (username))
        InfoData = cursor3.fetchall()
        DetailQuery = 'SELECT photoID, timestamp, fname, lname FROM photo NATURAL JOIN person NATURAL JOIN tag WHERE photoOwner = %s AND acceptedTag = 1 ORDER BY timestamp DESC'
        with conn.cursor() as cursor4:
            cursor4.execute(DetailQuery, (username))
        detail_data = cursor4.fetchall()
        tag_imageData = 'SELECT photoID, photoOwner, filePath FROM tag NATURAL JOIN photo WHERE username = %s AND acceptedTag = 1 AND (photoID) NOT IN (SELECT photoID FROM photo WHERE photoOwner = %s)'
        with conn.cursor() as cursor5:
            cursor5.execute(tag_imageData, (username, username))
        tagData = cursor5.fetchall()
        return render_template("images.html",photo_list = InfoData, images= image_data, photo_list2 = detail_data, tag_images = tag_data, tagData = tagData)
    else: #person is not tagged in any photo or only self-tagged
        image_query = 'SELECT filePath FROM photo WHERE photoOwner = %s ORDER BY timestamp DESC' #used for image 
        with conn.cursor() as cursor:
            cursor.execute(image_query, (username))
        image_data = cursor.fetchall()
        InfoQuery = 'SELECT photoID, photoOwner, caption FROM photo WHERE photoOwner = %s ORDER BY timestamp DESC'
        with conn.cursor() as cursor3:
            cursor3.execute(InfoQuery, (username))
        InfoData = cursor3.fetchall()
        DetailQuery = 'SELECT photoID, timestamp, fname, lname FROM photo NATURAL JOIN person NATURAL JOIN tag WHERE photoOwner = %s AND acceptedTag = 1 ORDER BY timestamp DESC'
        with conn.cursor() as cursor4:
            cursor4.execute(DetailQuery, (username))
        detail_data = cursor4.fetchall()
        return render_template("images.html",photo_list = InfoData, images = image_data, photo_list2 = detail_data)
    
    

@app.route('/add_friend', methods = ["GET","POST"]) 
def add_friend():
    username = session['username']
    friend = request.form['username']
    group_name = request.form['group_name']
    cursor = conn.cursor()
    check_query = 'SELECT username FROM Person NATURAL JOIN follow WHERE username = %s AND followerUsername = %s AND followeeUsername = %s AND acceptedfollow = 1 ' #error handling
    cursor.execute(check_query,(friend, username, friend))
    data = cursor.fetchone()
    error = None
    if (data):
        query = 'INSERT INTO belong VALUES(%s,%s,%s)'
        cursor.execute(query,(group_name,username,friend))
        conn.commit()
        cursor.close()
        return render_template('add_friend_message.html', friend_name = friend, username = username, groupName = group_name)
    else: 
        error = "You can't add this user to the group"
        return render_template('select_group.html',error = error)


@app.route('/select_group')
def select_group():
    #check that user is logged in
    username = session['username']
    cursor = conn.cursor();
    query = 'SELECT groupName FROM closefriendgroup WHERE groupOwner = %s '
    cursor.execute(query,username)
    data = cursor.fetchall()
    cursor.close()
    return render_template('select_group.html', user_list=data)

@app.route('/send_request', methods = ["GET","POST"])
def send_request():
    followee = request.form['followee'] #person who's receiving the request 
    follower_username = session['username'] #Person who's sending the request 
    cursor = conn.cursor();
    check_query = 'SELECT followerUsername, followeeUsername FROM follow WHERE followerUsername = %s AND followeeUsername = %s AND acceptedfollow = 0 OR followerUsername = %s AND followeeUsername = %s AND acceptedfollow = 1'
    cursor.execute(check_query,(follower_username,followee, follower_username,followee))
    data = cursor.fetchall()
    check_query2 = 'SELECT username FROM person WHERE username = %s'
    with conn.cursor() as cursor2:
        cursor2.execute(check_query2, (followee))
    data2 = cursor2.fetchone()
    error = None
    if (data): #when the followee name duplicate 
        error = "You already sent this user the request or followee already accepted your request"
        return render_template('send_request.html',error = error)
    elif (not data2):
        error = "This user does not exist"
        return render_template('send_request.html',error=error)
    else:
        query = 'INSERT INTO follow VALUES(%s,%s,False) '
        cursor.execute(query,(follower_username,followee))
        data = cursor.fetchall()
        cursor.close()
        return render_template('home.html',username = follower_username)


@app.route('/accept_follower', methods = ["GET","POST"])
def accept_follower():
    username = session['username']
    follower = request.args['followerUsername']
    accept = request.args['action']
    cursor = conn.cursor();
    if (accept == 'Accept Request'):
        query = 'UPDATE follow SET acceptedfollow = 1 WHERE followerUsername = %s AND followeeUsername = %s'
        cursor.execute(query,(follower,username))
        data = cursor.fetchall()
        cursor.close()
        return render_template('home.html',username = username)
    else:
        query = 'DELETE FROM follow WHERE followerUsername = %s AND followeeUsername = %s'
        cursor.execute(query,(follower,username))
        data = cursor.fetchall()
        cursor.close()
        return render_template('home.html',username = username)

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
