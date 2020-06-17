from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from forms import SignUpForm, TrackForm, LoginForm
from carbondata import carbon_em
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
#import pymysql
from flask_sqlalchemy  import SQLAlchemy
#from sqlalchemy.ext.automap import automap_base
#from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, TIMESTAMP
import googlemaps # importing googlemaps module

app = Flask(__name__) # app is the Flask object with __name__ as the root path
app.config['SECRET_KEY'] = 'secret'
csrf = CSRFProtect(app)

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="",
    password="",
    hostname="",
    databasename="",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    username = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(60), unique=True)
    password = db.Column(db.String(80), unique=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calc_carb(orig,destin,car):
    # Requires API key
    gmaps = googlemaps.Client(key='Enter your key')
    # Requires cities name
    my_dist = gmaps.distance_matrix(orig,destin)['rows'][0]['elements'][0]
    distance_metres = my_dist['distance']['value']
    dist_km = distance_metres/1000
    CO2 = car*dist_km
    return dist_km,orig.split(',')[0].replace('+',' '),destin.split(',')[0].replace('+',' '),round(CO2,2)

@app.route("/", methods=['GET', 'POST'])
def land():
    return render_template('land.html')


@app.route("/set_target") # homepage of our website
def set_target():
    results=1
    return render_template('set_target.html', results=results)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        UName = request.form['name']
        user_name = request.form['username']
        Uemail = request.form['email']
        Upassword = request.form['password']
        hashed_pass = generate_password_hash(Upassword, method='sha256')
        new_user = User(name=UName, username=user_name, email=Uemail, password=hashed_pass)
        db.session.add(new_user)
        db.session.commit()

        #hashed_pass = generate_password_hash(Upassword, method='sha256')

        return render_template('new_user.html')
        #return '<h1>' + UName + '' + user_name + Uemail + Upassword + '</h>'
        #return render_template('user.html')
    return render_template('signup.html', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_tmp = request.form['username_typed']
        user = User.query.filter_by(username=user_tmp).first()
        password_tmp = request.form['password_typed']
        if user:
            print("User Exists!")
            if check_password_hash(user.password, password_tmp):
                login_user(user, remember=False)
                return redirect(url_for('show_user_profile', username=user_tmp))
            else:
                flash('Wrong password!')
                return redirect(url_for('login'))
        else:
            return '<h4 align="center">User not found</h4>'
        #return '<h1>' + user_tmp + ' ' + password_tmp + '</h>'
        #redirect(url_for('show_user_profile', username='test'))
    return render_template('login.html', form=form)

@app.route('/user/<username>')
@login_required
def show_user_profile(username):
     return render_template('profile.html', name=current_user.name)


@app.route('/user/carbon_offset/')
def carbon_off():
     return render_template('carbon_offset.html')

@app.route('/user/leaderboard')
def leader():
     return render_template('leader.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('land'))

@app.route('/user/lemon/test')
def lemon():
     return render_template('test.html')

@app.route('/user/lemon/test-land')
def lemon_land():
    form = TrackForm()
    return render_template('test-land.html', form=form)

@app.route("/track", methods=['GET', 'POST'])
def track():
    form_tr = TrackForm()
    engine_dropdown = carbon_em.loc[(carbon_em['category_of_vehicle'] == 'bus'), 'engine__cc']
    form_tr.engine.choices = [(i.lower().replace(' ', '_'), i.replace('_', ' ')) for i in engine_dropdown]
    fuel_dropdown = carbon_em.loc[((carbon_em['category_of_vehicle'] == 'bus') &
                         (carbon_em['engine__cc'] == 'none')), 'fuel']
    form_tr.fuel.choices = [(i.lower().replace(' ', '_'), i.replace('_', ' ')) for i in fuel_dropdown]
    if form_tr.is_submitted():
        origin = request.form['origin'].replace(' ','+')
        destination = request.form['dest'].replace(' ','+')
        select_vehicle = request.form['vehicle']
        select_engine = request.form['engine']
        select_fuel = request.form['fuel']
        val = carbon_em.loc[((carbon_em['category_of_vehicle'] == select_vehicle)
                             & (carbon_em['engine__cc'] == select_engine)
                             & (carbon_em['fuel'] == select_fuel)), 'emission_factor(kgco2perkm)']
        print(select_vehicle, select_engine, select_fuel,val)
        carbon_out = calc_carb(origin,destination,float(val))
        return render_template('carbon_out.html', result=carbon_out)
    return render_template('track.html', form=form_tr)

@app.route("/city/<vehicle>", methods=['GET', 'POST'])
def engine(vehicle):

    eng_op = carbon_em.loc[(carbon_em['category_of_vehicle'] == vehicle),'engine__cc']
    engine = [(i.lower().replace(' ', '_'), i.replace('_', ' ')) for i in eng_op]
    engineArray = [{'id': 'Please select', 'value': '0'}]

    for eng in set(engine):
        engObj  = {}
        engObj['id'] = eng[1]
        engObj['value'] = eng[0]
        engineArray.append(engObj)
    return jsonify({ 'engine' : engineArray })

@app.route("/city/<vehicle>/<engine>", methods=['GET', 'POST'])
def fuel(vehicle, engine):

    fuel_op = carbon_em.loc[((carbon_em['category_of_vehicle'] == vehicle)
                             & (carbon_em['engine__cc'] == engine)),'fuel']
    fuel = [(i.lower().replace(' ', '_'), i.replace('_', ' ')) for i in fuel_op]
    fuelArray = [{'id': 'Please select', 'value': '0'}]

    for f in set(fuel):
        fuelObj  = {}
        fuelObj['id'] = f[1]
        fuelObj['value'] = f[0]
        fuelArray.append(fuelObj)
    return jsonify({ 'fuel' : fuelArray })


if __name__ == "__main__": #check to oonly run the webserver if this file is called directly
    app.run(debug=True) # start webserver
