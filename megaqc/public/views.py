# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, abort, json, Request
from flask_login import login_required, login_user, logout_user, current_user

from collections import OrderedDict

from megaqc.extensions import login_manager, db
from megaqc.public.forms import LoginForm
from megaqc.user.forms import RegisterForm
from megaqc.user.models import User
from megaqc.model.models import Report, PlotConfig, PlotData, PlotCategory
from megaqc.api.utils import get_samples, get_reports_data, get_user_filters, aggregate_new_parameters, get_report_metadata_fields, get_queued_uploads, get_plot_favourites, get_favourite_plot_data
from megaqc.utils import settings, flash_errors

from sqlalchemy.sql import func, distinct
from urllib import unquote_plus

blueprint = Blueprint('public', __name__, static_folder='../static')


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.get(int(user_id))

@blueprint.route('/', methods=['GET', 'POST'])
def home():
    """Home page."""
    return render_template(
        'public/home.html',
        num_samples = get_samples(count=True),
        num_reports = get_reports_data(count=True),
        num_uploads_processing = get_queued_uploads(count=True, filter_cats=["NOT TREATED", "IN TREATMENT"])
    )

@blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    """Log in."""
    form = LoginForm(request.form)
    # Handle logging in
    if request.method == 'POST':
        if form.validate_on_submit():
            login_user(form.user)
            flash('Welcome {}! You are now logged in.'.format(current_user.first_name), 'success')
            redirect_url = request.args.get('next') or url_for('public.home')
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template('public/login.html', form=form)

@blueprint.route('/logout/')
@login_required
def logout():
    """Logout."""
    logout_user()
    flash('You are logged out.', 'info')
    return redirect(url_for('public.home'))


@blueprint.route('/register/', methods=['GET', 'POST'])
def register():
    """Register new user."""
    form = RegisterForm(request.form, csrf_enabled=False)
    if form.validate_on_submit():
        user_id = (db.session.query(func.max(User.user_id)).scalar() or 0)+1
        User.create(
            user_id = user_id,
            username = form.username.data,
            email = form.email.data,
            password = form.password.data,
            first_name = form.first_name.data,
            last_name = form.last_name.data,
            active = True
        )
        flash("Thanks for registering! You're now logged in.", 'success')
        return redirect(url_for('public.home'))
    else:
        flash_errors(form)
    return render_template('public/register.html', form=form)


@blueprint.route('/about/')
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template('public/about.html', form=form)

@blueprint.route('/plot_type/')
def choose_plot_type():
    """Choose plot type."""
    return render_template('public/plot_type.html', num_samples=get_samples(count=True))

@blueprint.route('/report_plot/')
@login_required
def report_plot():
    # Get the fields from the add-new-filters form
    return_data = aggregate_new_parameters(current_user,[], False)
    sample_filters=order_sample_filters()
    return render_template(
        'public/report_plot.html',
        db = db,
        User = User,
        user_token = current_user.api_token,
        sample_filters = sample_filters,
        num_samples = return_data[0],
        report_fields_json = json.dumps(return_data[1]),
        sample_fields_json = json.dumps(return_data[2]),
        report_plot_types = return_data[3]
        )

@blueprint.route('/queued_uploads/')
@login_required
def queued_uploads():
    return render_template(
        'users/queued_uploads.html',
        db = db,
        User = User,
        user_token = current_user.api_token,
        uploads = get_queued_uploads()
        )

@blueprint.route('/plot_favourites/')
@login_required
def plot_favourites():
    """View and edit saved plots."""
    return render_template(
        'users/plot_favourites.html',
        favourite_plots = get_plot_favourites(User),
        user_token = current_user.api_token,
    )

@blueprint.route('/plot_favourite/<fav_id>')
@blueprint.route('/plot_favourite/<fav_id>/raw')
@login_required
def plot_favourite(fav_id):
    """View and edit saved plots."""
    return render_template(
        'users/plot_favourite.html',
        plot_data = get_favourite_plot_data(current_user, fav_id),
        raw = request.path.endswith('/raw'),
        user_token = current_user.api_token,
    )

@blueprint.route('/edit_filters/')
@login_required
def edit_filters():
    """Edit saved filters."""
    sample_filters = order_sample_filters()
    sample_filter_counts = {}
    for sfg in sample_filters:
        sample_filter_counts[sfg] = {}
        for sf in sample_filters[sfg]:
            sample_filter_counts[sf['id']] = get_samples(filters=sf['id'], count=True)
    return render_template(
        'users/organize_filters.html',
        sample_filters = sample_filters,
        sample_filter_counts = sample_filter_counts,
        user_token = current_user.api_token,
        num_samples = get_samples(count=True)
    )

def order_sample_filters():
    sample_filters = OrderedDict()
    sample_filters['Global'] = [{
        'id': -1,
        'set': 'Global',
        'name': 'All Samples'
    }]
    for sf in get_user_filters(current_user):
        if sf['set'] not in sample_filters:
            sample_filters[sf['set']] = list()
        sample_filters[sf['set']].append(sf)
    return sample_filters


@blueprint.route('/distributions/')
@login_required
def distributions():
    # Get the fields from the add-new-filters form
    return_data = aggregate_new_parameters(current_user, [], False)
    sample_filters = order_sample_filters()
    return render_template(
        'public/distributions.html',
        db = db,
        User = User,
        user_token = current_user.api_token,
        sample_filters = sample_filters,
        num_samples = return_data[0],
        report_fields = return_data[1],
        sample_fields = return_data[2],
        report_fields_json = json.dumps(return_data[1]),
        sample_fields_json = json.dumps(return_data[2])
        )

@blueprint.route('/trends/')
@login_required
def trends():
    # Get the fields from the add-new-filters form
    return_data = aggregate_new_parameters(current_user, [], False)
    sample_filters = order_sample_filters()
    return render_template(
        'public/trends.html',
        db = db,
        User = User,
        user_token = current_user.api_token,
        sample_filters = sample_filters,
        num_samples = return_data[0],
        report_fields = return_data[1],
        sample_fields = return_data[2],
        report_fields_json = json.dumps(return_data[1]),
        sample_fields_json = json.dumps(return_data[2])
        )

@blueprint.route('/comparisons/')
@login_required
def comparisons():
    # Get the fields from the add-new-filters form
    return_data = aggregate_new_parameters(current_user, [], False)
    sample_filters = order_sample_filters()
    return render_template(
        'public/comparisons.html',
        db = db,
        User = User,
        user_token = current_user.api_token,
        sample_filters = sample_filters,
        num_samples = return_data[0],
        report_fields = return_data[1],
        sample_fields = return_data[2],
        report_fields_json = json.dumps(return_data[1]),
        sample_fields_json = json.dumps(return_data[2])
        )

@blueprint.route('/edit_reports/')
@login_required
def edit_reports():
    # Get the fields from the add-new-filters form
    user_id = None
    if not current_user.is_admin:
        user_id=current_user.user_id
    return_data = get_reports_data(False, user_id)
    return render_template(
        'public/reports_management.html',
        report_data=return_data,
        report_meta_fields=get_report_metadata_fields(),
        api_token=current_user.api_token)
