# -*- coding: utf-8 -*-

'''
This is the most important file for the web app. It contains the various
routes that end users can use.

For instance

@app.route('/about/', methods=['GET'])
def about():
    return render_template("info/about.html")

Where /about/ is the link.
'''

from __future__ import absolute_import

import os
import pandas as pd

from flask import Flask, render_template, url_for, redirect, request
from werkzeug import secure_filename

from flask.ext.admin.contrib import sqla
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask.ext.admin.contrib.sqla.view import func
from flask_admin.form import BaseForm
from flask_admin.contrib.sqla import tools
from flask_mail import Mail
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from wtforms.fields import SelectField, StringField
from sqlalchemy import or_

from clic.web.api import api, fetchClusters, fetchKeywords
from clic.chapter_repository import ChapterRepository
from clic.kwicgrouper import KWICgrouper, concordance_for_line_by_line_file
from clic.web.forms import BOOKS, SUBSETS
from clic.web.models import db, Annotation, Category, Role, User, List, Tag, Note, Subset

app = Flask(__name__, static_url_path='')
app.register_blueprint(api, url_prefix='/api')
app.config.from_pyfile('config.py')
mail = Mail(app)
db.init_app(app)

# Setup Flask-Security
# add a custom form:
# https://pythonhosted.org/Flask-Security/customizing.html#forms
from flask_security.forms import RegisterForm
from wtforms import TextField
from wtforms.validators import Required

class ExtendedRegisterForm(RegisterForm):
    name = TextField('Name', [Required()])

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, register_form=ExtendedRegisterForm)

'''
Application routes
'''

#==============================================================================
# Home, about, docs, 404
#==============================================================================
@app.route('/', methods=['GET'])
def index():
    return render_template("info/home.html")

@app.route('/about/', methods=['GET'])
def about():
    return render_template("info/about.html")

@app.route('/documentation/', methods=['GET'])
def documentation():
    return render_template("info/documentation.html")

@app.route('/releases/', methods=['GET'])
def releases():
    return render_template("info/releases.html")

@app.route('/blog/', methods=['GET'])
def blog():
    return render_template("info/blog.html")

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
def chapterView(number, book, word_index=None, search_term=None):
    chapter_repository = ChapterRepository()

    if word_index is None:
        chapter, book_title = chapter_repository.get_chapter(number, book)
    else:
        chapter, book_title = chapter_repository.get_chapter_with_highlighted_search_term(number, book, word_index, search_term)

    return render_template("chapter-view.html", content=chapter, book_title=book_title)

#==============================================================================
# Subsets
#==============================================================================
@app.route('/subsets/', methods=["GET"])
def subsets():
    """
    This is a quick and dirty method to display the subsets in our db.
    It now uses GET parameters, but should probably use POST parameters
    ideally.
    The basic design for POST parameters was almost ready but there were a
    few issues.
    """


    book = request.args.get('book')
    subset = request.args.get('subset')

    if book and subset:
        return redirect(url_for('subsets_display',
                                book=book,
                                subset=subset))

    return render_template("subsets-form.html")


@app.route('/subsets/<book>/<subset>/', methods=["GET", "POST"])
def subsets_display(book=None, subset=None):

    if book and subset:
        # make sure they are not malicious names
        book = secure_filename(book)
        subset = secure_filename(subset)

        if book not in BOOKS:
            return redirect(url_for('page_not_found'))

        if subset not in SUBSETS:
            return redirect(url_for('page_not_found'))

        BASE_DIR = os.path.dirname(__file__)
        filename = "../textfiles/{0}/{1}_{0}.txt".format(subset, book)
        with open(os.path.join(BASE_DIR, filename), 'r') as the_file:
            result = the_file.readlines()

        return render_template("subsets-results.html",
                               book=book,
                               subset=subset,
                               result=result,
                               )

    else:
        return redirect(url_for('subsets'))

#==============================================================================
# 404
#==============================================================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page-not-found.html'), 404

#==============================================================================
# KWICgrouper
#==============================================================================

@app.route('/patterns/', methods=["GET"])
def patterns():

    if not 'term' in request.args.keys():
        return render_template("patterns-form.html")

    else:

        # MAKE DRY
        book = request.args.get('book')
        subset = request.args.get('subset')
        term = request.args.get('term').strip()
        local_args = dict(request.args)

        kwic_filter = {}
        for key,value in local_args.iteritems():
            if key == "subset" or key == "book" or key == "term":
                pass
            elif value[0]:
                # the values are in the first el of the list
                # 'L2': [u'a']
                values = value[0]
                values = values.split(",")
                values = [value.strip() for value in values]
                kwic_filter[key] = values

        if book and subset:
            # make sure they are not malicious names
            book = secure_filename(book)
            subset = secure_filename(subset)

            if book not in BOOKS:
                return redirect(url_for('page_not_found'))

            if subset not in SUBSETS:
                return redirect(url_for('page_not_found'))

            BASE_DIR = os.path.dirname(__file__)
            filename = "../textfiles/{0}/{1}_{0}.txt".format(subset, book)
            concordance = concordance_for_line_by_line_file(os.path.join(BASE_DIR, filename), term)
            # should not be done here
            if not concordance:
                return render_template("patterns-noresults.html")
            kwicgrouper = KWICgrouper(concordance)
            textframe = kwicgrouper.filter_textframe(kwic_filter)

            collocation_table = textframe.apply(pd.Series.value_counts, axis=0)
            collocation_table["Sum"] = collocation_table.sum(axis=1)
            collocation_table["Left Sum"] = collocation_table[["L5","L4","L3","L2","L1"]].sum(axis=1)
            collocation_table["Right Sum"] = collocation_table[["R5","R4","R3","R2","R1"]].sum(axis=1)

            pd.set_option('display.max_colwidth', 1000)

            # replicate the index so that it is accessible from a row-level apply function
            # http://stackoverflow.com/questions/20035518/insert-a-link-inside-a-pandas-table
            collocation_table["collocate"] = collocation_table.index

            # function that can be applied
            def linkify(row, position, term=None, book=None, subset=None):
                """
                The purpose is to make links in the dataframe.to_html() output clickable.

                # http://stackoverflow.com/a/26614921
                """
                if pd.notnull(row[position]):
                    return """<a href="/patterns/?{0}={1}&term={2}&book={4}&subset={5}">{3}</a>""".format(position,
                                                                                      row["collocate"],
                                                                                      term,
                                                                                      int(row[position]),
                                                                                      book,
                                                                                      subset
                                                                                     )

            # http://localhost:5000/patterns/?L5=&L4=&L3=&L2=&L1=&term=voice&R1=&R2=&R3=&R4=&R5=&subset=long_suspensions&book=BH

            def linkify_process(df, term, book, subset):
                """
                Linkifies every column from L5-R5
                """
                for itm in "L5 L4 L3 L2 L1 R1 R2 R3 R4 R5".split():
                    df[itm] = df.apply(linkify, args=([itm, term, book, subset]), axis=1)
                return df



            linkify_process(collocation_table, term, book, subset)
            del collocation_table["collocate"]


            collocation_table = collocation_table[collocation_table.index != ""]

            collocation_table = collocation_table.fillna("").to_html(classes=["table", "table-striped", "table-hover", "dataTable", "no-footer", "uonDatatable", 'my_class" id = "dataTableCollocation'],
                                                                                            bold_rows=False,
                                                                                 ).replace("&lt;", "<").replace("&gt;", ">")


            bookname = book
            subsetname = subset.replace("_", " ").capitalize()

            # this bit is a hack:
            # classes = 'my_class" id = "my_id'
            # http://stackoverflow.com/questions/15079118/js-datatables-from-pandas
            return render_template("patterns-results.html",
                                   textframe=textframe,
                                   # local_args=kwic_filter,
                                   collocation_table=collocation_table,
                                   bookname=bookname,
                                   subsetname=subsetname)



#==============================================================================
# User annotation of subsets using Flask_admin
#==============================================================================

class SubsetModelView(ModelView):
    # 'notes.owner.name' works, but cannot be distinguished
    # column_filters = ('book', 'abbr', 'kind', 'corpus', 'text', 'notes', 'tags', 'tags.owner.name', 'tags.owner.email', )
    column_filters = ('book', 'abbr', 'kind', 'text', 'notes', 'tags', 'tags.owner.name', 'tags.owner.email', )
    column_searchable_list = ('abbr', 'text',)
    column_list = ('book', 'kind', 'text', 'tags', 'notes')
    # column_list = ('book', 'text',)
    # column_exclude_list = ['abbr','corpus']
    # column_editable_list could work with the above code included, but not great
    # column_editable_list = ['tags', 'notes']
    column_hide_backrefs = False
    named_filter_urls = True

    # editing
    edit_modal = True
    form_excluded_columns = ['book', 'abbr', 'kind', 'corpus', 'text',]
    # nice but not what we are looking for:
    # inline_models = (Tag, Note)

    # can_view_details = True
    can_create = False
    can_delete = False  # disable model deletion
    can_edit = True  # TODO disable editable fields
    can_export = True  # FIXME
    export_max_rows = 2000

    page_size = 50  # the number of entries to display on the list view

    def is_accessible(self):
        # return current_user.has_role('can_annotate')
        return current_user.is_active()

    # def edit_form(self, obj):
    #     return self._use_filtered_tags(super(SubsetModelView, self).edit_form(obj))
    #
    # def _use_filtered_tags(self, form):
    #     form.tags.query_factory = self._get_tags_list
    #     return form
    #
    # def _get_tags_list(self):
    #     return self.session.query(Tag).filter_by(owner=current_user).all()


class TagModelView(ModelView):
    action_disallowed_list = ['delete',]
    form_excluded_columns = ['subset',]
    column_editable_list = ['tag_name',]
    named_filter_urls = True
    # column_filters = ['owner.name', 'tag_name']
    column_filters = ['tag_name']

    def is_accessible(self):
        # return current_user.has_role('can_annotate')
        return current_user.is_active()

    # http://stackoverflow.com/a/30741433/2115409
    def get_query(self):
       return self.session.query(self.model).filter(self.model.owner == current_user)

    # http://stackoverflow.com/a/26351005/2115409
    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.owner==current_user)

    def create_form(self):
        return self._use_filtered_owner(super(TagModelView, self).create_form())

    def edit_form(self, obj):
        return self._use_filtered_owner(super(TagModelView, self).edit_form(obj))

    def _use_filtered_owner(self, form):
        form.owner.query_factory = self._get_owner_list
        return form

    def _get_owner_list(self):
        return self.session.query(User).filter_by(id=current_user.id).all()


class NoteModelView(ModelView):
    action_disallowed_list = ['delete',]
    column_editable_list = ['note',]
    form_excluded_columns = ['subset',]
    column_list = ('owner','note',)
    named_filter_urls = True
    column_filters = ('owner.name', 'note',)

    def is_accessible(self):
        # return current_user.has_role('can_annotate')
        return current_user.is_active()

    # http://stackoverflow.com/a/30741433/2115409
    def get_query(self):
       return self.session.query(self.model).filter(self.model.owner == current_user)

    # http://stackoverflow.com/a/26351005/2115409
    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.owner==current_user)

    def create_form(self):
        return self._use_filtered_owner(super(NoteModelView, self).create_form())

    def edit_form(self, obj):
        return self._use_filtered_owner(super(NoteModelView, self).edit_form(obj))

    def _use_filtered_owner(self, form):
        form.owner.query_factory = self._get_owner_list
        return form

    def _get_owner_list(self):
        return self.session.query(User).filter_by(id=current_user.id).all()


class UserAdmin(sqla.ModelView):

    # Prevent administration of Users unless the currently logged-in user has the "superman" role
    def is_accessible(self):
       return current_user.has_role('superman')


class RoleAdmin(sqla.ModelView):

    # Prevent administration of Roles unless the currently logged-in user has the "superman" role
    def is_accessible(self):
        return current_user.has_role('superman')


admin = Admin(
    app,
    template_mode='bootstrap3',
    index_view=AdminIndexView(
        name='Documentation',
        url='/annotation',
        template="user-annotation.html",
        )
    )

admin.add_view(SubsetModelView(Subset, db.session))
admin.add_view(TagModelView(Tag, db.session))
admin.add_view(NoteModelView(Note, db.session))
admin.add_view(UserAdmin(User, db.session))
admin.add_view(RoleAdmin(Role, db.session))

if __name__ == '__main__':

    @app.before_first_request
    def initialize_database():
        db.create_all()

    from flask_debugtoolbar import DebugToolbarExtension
    app.debug = True
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=5000, debug=True)
