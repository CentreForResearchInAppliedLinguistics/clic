from __future__ import absolute_import  ## help python find modules within clic package (see John H email 09.04.2014)
from flask import Flask, render_template, url_for, redirect, request

from clic.web.api import api, fetchClusters, fetchKeywords
from clic.chapter_repository import ChapterRepository

app = Flask(__name__, static_url_path='')
app.register_blueprint(api, url_prefix='/api')

#TODO delete:
# from flask_debugtoolbar import DebugToolbarExtension
# app.debug = True
# app.config["SECRET_KEY"] = "jadajajada"
# toolbar = DebugToolbarExtension(app)

'''
Application routes
'''

#==============================================================================
# Home, about, docs, 404
#==============================================================================
@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('concordances')) # current home page. may change

@app.route('/about/', methods=['GET'])
def about():
    return render_template("about.html")

@app.route('/documentation/', methods=['GET'])
def documentation():
    return render_template("documentation.html")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page-not-found.html'), 404

#==============================================================================
# Concordances
#==============================================================================
@app.route('/concordances/', methods=['GET'])
def concordances():
    if 'terms' in request.args.keys(): # form was submitted
        return render_template("concordance-results.html")
    else:
        return render_template("concordance-form.html")

#==============================================================================
# Keywords
#==============================================================================
@app.route('/keywords/', methods=['GET'])
def keywords():
    if 'testIdxGroup' in request.args.keys(): # form was submitted

        # get parameters for redirecting to the concordance page
        IdxGroup = request.args.get('testIdxGroup')
        testCollection = request.args.get('testCollection')
        testIdxMod = request.args.get('testIdxMod')
        selectWords = "whole"

        args = request.args
        keywords_result = fetchKeywords(args)

        return render_template("keywords-results.html",
                               IdxGroup=IdxGroup,
                               testCollection=testCollection,
                               testIdxMod=testIdxMod,
                               selectWords=selectWords,
                               keywords=keywords_result)

    else:
        return render_template("keywords-form.html")

#==============================================================================
# Clusters
#==============================================================================
@app.route('/clusters/', methods=['GET'])
def clusters():
    if 'testIdxGroup' in request.args.keys(): # form was submitted

        IdxGroup = request.args.get('testIdxGroup')
        # FIXME this might not work when dealing with only a few books,
        # rather than an entire subcorpus, in that case better use:
        # collection = args.getlist('testCollection') ## args is a 
        ## multiDictionary: use .getlist() to access individual books
        testCollection = request.args.get('testCollection')
        testIdxMod = request.args.get('testIdxMod')
        selectWords = "whole"
        
        args = request.args
        clusters_result = fetchClusters(args)

        return render_template("clusters-results.html",
                               IdxGroup=IdxGroup,
                               testCollection=testCollection,
                               testIdxMod=testIdxMod,
                               selectWords=selectWords,
                               clusters=clusters_result)

    else:
        return render_template("clusters-form.html")

#==============================================================================
# Chapters
#==============================================================================
@app.route('/chapter/<book>/<int:number>/')
@app.route('/chapter/<book>/<int:number>/<int:word_index>/<search_term>/')
def chapterView(number, book, word_index = None, search_term = None):
    chapter_repository = ChapterRepository()

    if word_index is None:
        chapter, book_title = chapter_repository.get_chapter(number, book)
    else:
        chapter, book_title = chapter_repository.get_chapter_with_highlighted_search_term(number, book, word_index, search_term)

    return render_template("chapter-view.html", content=chapter, book_title=book_title)

# TODO delete?
#if __name__ == '__main__':
#   app.run()