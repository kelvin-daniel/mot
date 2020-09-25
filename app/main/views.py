from flask import render_template,request,redirect,url_for,abort
from . import main
from ..requests import get_movies,get_movie,search_movie
from .forms import ReviewForm,UpdateProfile
from ..models import Review,User,PhotoProfile
from flask_login import login_required,current_user
from .. import db,photos
import markdown2  
import warnings
import pandas as pd
import numpy as np
import smtplib

warnings.filterwarnings("ignore")

# Views
@main.route('/')
def index():

    '''
    View root page function that returns the index page and its data
    '''

    # Getting popular movie
    popular_movies = get_movies('popular')
    upcoming_movie = get_movies('upcoming')
    now_showing_movie = get_movies('now_playing')

    title = 'Home - Welcome to The best Movie Review Website Online'

    search_movie = request.args.get('movie_query')

    if search_movie:
        return redirect(url_for('.search',movie_name=search_movie))
    else:
        return render_template('index.html', title = title, popular = popular_movies, upcoming = upcoming_movie, now_showing = now_showing_movie )


@main.route('/movie/<int:id>')
def movie(id):

    '''
    View movie page function that returns the movie details page and its data
    '''
    movie = get_movie(id)
    title = f'{movie.title}'
    reviews = Review.get_reviews(movie.id)

    return render_template('movie.html',title = title,movie = movie,reviews = reviews)



@main.route('/search/<movie_name>')
def search(movie_name):
    '''
    View function to display the search results
    '''
    movie_name_list = movie_name.split(" ")
    movie_name_format = "+".join(movie_name_list)
    searched_movies = search_movie(movie_name_format)
    title = f'search results for {movie_name}'
    return render_template('search.html',movies = searched_movies)


@main.route('/movie/review/new/<int:id>', methods = ['GET','POST'])
@login_required
def new_review(id):
    form = ReviewForm()
    movie = get_movie(id)
    if form.validate_on_submit():
        title = form.title.data
        review = form.review.data

        # Updated review instance
        new_review = Review(movie_id=movie.id,movie_title=title,image_path=movie.poster,movie_review=review,user=current_user)

        # save review method
        new_review.save_review()
        return redirect(url_for('.movie',id = movie.id ))

    title = f'{movie.title} review'
    return render_template('new_review.html',title = title, review_form=form, movie=movie)

@main.route('/user/<uname>')
@login_required
def profile(uname):
    user = User.query.filter_by(username = uname).first()

    if user is None:
        abort(404)

    return render_template("profile/profile.html", user = user)


@main.route('/user/<uname>/update',methods = ['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(username = uname).first()
    if user is None:
        abort(404)

    form = UpdateProfile()

    if form.validate_on_submit():

        user.bio = form.bio.data

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.profile',uname=user.username))

    return render_template('profile/update.html',form =form)


@main.route('/user/<uname>/update/pic',methods= ['POST'])
@login_required
def update_pic(uname):
    user = User.query.filter_by(username = uname).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        user_photo = PhotoProfile(pic_path = path,user = user)
        db.session.commit()
    return redirect(url_for('main.profile',uname=uname))

@main.route('/review/<int:id>')
def single_review(id):
    review=Review.query.get(id)
    if review is None:
        abort(404)
    format_review = markdown2.markdown(review.movie_review,extras=["code-friendly", "fenced-code-blocks"])
    return render_template('review.html',review = review,format_review=format_review)

@main.route('/recommendation')
def recommendation():
    movies_titles = pd.read_csv("data/Movie_Id_Titles")
    movies_list = movies_titles['title'].values.tolist()
    return render_template('recommenndation.html',movies = movies_list)

@main.route('/predict', methods=['POST'])
def predict():
    column_names = ['user_id','item_id','rating','timestamp']
    df = pd.read_csv("data/u.data",sep="\t",names=column_names)
    movie_titles = pd.read_csv("data/Movie_Id_Titles")
    df = pd.merge(df,movie_titles,on='item_id')

    ratings = pd.DataFrame(df.groupby('title')['rating'].mean())
    ratings['num_of_ratings'] = pd.DataFrame(df.groupby('title')['rating'].count())
    moviemat = df.pivot_table(values='rating',index='user_id',columns='title')

    argument = request.form['choice']
    user_name = request.form['username']
    starwars_ratings = moviemat[argument]
    starwars_ratings.dropna(inplace=True)
    corr_starwars = moviemat.corrwith(starwars_ratings)
    like_starwars = pd.DataFrame(corr_starwars,columns=['Correlation'])
    like_starwars.dropna(inplace=True)
    like_starwars = like_starwars.join(ratings['num_of_ratings'])
    like_starwars = like_starwars.join(ratings['rating'])
    result = like_starwars[like_starwars['num_of_ratings']>100].sort_values('Correlation',ascending=False)
    res=result.index[1:11]
    res_df = pd.DataFrame(data=res)
    recommendations = res_df['title'].values.tolist()
    movie_rating = result['rating'].values.tolist()

    from_email = 'testingemailpk6@gmail.com'
    password = 'moringatest96'
    send_to_email = request.form['e_mail']
    message = '\n'.join(recommendations)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email, send_to_email , message)
    server.quit()



    return render_template('profile/profile.html',prediction = recommendations,username = user_name)
