# -*- coding: utf-8 -*-
"""
    wakatime.polls.views
    ~~~~~~~~~~~~~~~~~~~~

    Html views.
"""

import traceback
from urllib.parse import urlparse

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from psycopg2.errors import QueryCanceled
from sqlalchemy.exc import OperationalError

from wakatime import api_utils, app, auth, utils
from wakatime.forms import PollForm
from wakatime.models import Poll, db

from .utils import get_poll_image, make_image_response

blueprint = Blueprint("polls", __name__, template_folder="templates/polls")


@blueprint.route("/")
def index():
    if not app.current_user.is_authenticated:
        return render_template("/polls/marketing.html")
    return render_template("/polls/index.html", polls=app.current_user.polls.order_by(Poll.created_at.desc()).all())


@blueprint.route("/new", methods=["GET", "POST"])
@auth.login_required
@api_utils.rate_limited
def poll_new():
    if app.current_user.polls.count() > 40:
        api_utils.add_toast("You’ve created the maximum number of polls. Please delete one before creating another.", level="error")
        return redirect(url_for(".index"))

    form = PollForm(request.form)
    if request.method == "POST" and form.validate():
        poll = Poll(user_id=app.current_user.id, choices=form.data["choices"].splitlines())
        db.session.add(poll)
        db.session.commit()
        api_utils.add_toast("Poll created.", level="success")
        return redirect(url_for(".index"))

    return render_template("/polls/new.html", form=form), 200 if len(form.errors) == 0 else 400


@blueprint.route("/<string:poll_id>/edit", methods=["GET", "POST"])
@auth.login_required
def poll_edit(poll_id):
    poll = None
    if utils.is_uuid4(poll_id):
        poll = Poll.query.filter_by(user_id=app.current_user.id, id=poll_id).first()
    if not poll:
        abort(404)

    form = PollForm(request.form if request.form.get("choices") else None, data={"choices": "\n".join(poll.choices)})
    if request.method == "POST" and form.validate():
        poll.choices = form.data["choices"].splitlines()
        db.session.commit()
        api_utils.add_toast("Saved.", level="success")
        return redirect(url_for(".index"))

    return render_template("/polls/edit.html", form=form), 200 if len(form.errors) == 0 else 400


@blueprint.route("/<string:poll_id>/delete", methods=["POST"])
@auth.login_required
def poll_delete(poll_id):
    poll = None
    if utils.is_uuid4(poll_id):
        poll = Poll.query.filter_by(user_id=app.current_user.id, id=poll_id).first()
    if not poll:
        abort(404)

    poll.delete()

    api_utils.add_toast("Deleted.", level="success")
    return redirect(url_for(".index"))


@blueprint.route("/<string:poll_id>", methods=["GET", "POST"])
def poll_vote(poll_id):
    poll = None
    if utils.is_uuid4(poll_id):
        poll = Poll.query.filter_by(id=poll_id).first()
    if not poll:
        abort(404)

    if not app.current_user.is_authenticated or not app.current_user._has_github_login:
        next_url = request.url
        if request.referrer:
            try:
                referrer = urlparse(request.referrer)
                if referrer.hostname and referrer.hostname == "github.com":
                    next_url = utils.add_params_to_url(next_url, {"github_url": request.referrer})
            except:
                pass

        return redirect(
            utils.add_params_to_url(
                "/oauth/github/authorize",
                params={
                    "reason": "login",
                    "next": next_url,
                },
            )
        )

    github_url = request.args.get("github_url")
    if request.referrer and not github_url:
        try:
            referrer = urlparse(request.referrer)
            if referrer.hostname and referrer.hostname == "github.com":
                return redirect(utils.add_params_to_url(f"/polls/{poll.id}", {"github_url": request.referrer}))
        except:
            pass

    if request.method == "POST":
        poll.vote_for(request.form.get("choice"))
        next_url = "/polls"
        try:
            referrer = urlparse(github_url)
            if referrer.hostname and referrer.hostname == "github.com":
                next_url = github_url
        except:
            pass
        return redirect(next_url)

    return render_template("/polls/vote.html", poll=poll, bootstrap={"poll_id": poll.id})


@blueprint.route("/<string:poll_id>/unvote", methods=["POST"])
@auth.login_required
def poll_unvote(poll_id):
    poll = None
    if utils.is_uuid4(poll_id):
        poll = Poll.query.filter_by(id=poll_id).first()
    if not poll:
        abort(404)

    choice = utils.safe_unicode(utils.replace_whitespace(utils.remove_nulls(api_utils.get_request_json().get("choice"))))
    if choice:
        poll.remove_vote_for(choice)

    return jsonify(data={})


@blueprint.route("/<string:poll_id>.png")
@utils.crossdomain(origins=["*"])
def poll_png(poll_id):
    poll = None
    if utils.is_uuid4(poll_id):
        poll = Poll.query.filter_by(id=poll_id).first()
    if not poll:
        abort(404)

    refresh = request.args.get("refresh") == "true"
    try:
        return get_poll_image(poll, refresh=refresh)
    except (QueryCanceled, OperationalError):
        app.logger.error(traceback.format_exc())
        return make_image_response("updating in background... will be available in a few seconds"), 202
    except:
        app.logger.error(traceback.format_exc())
        return make_image_response("internal server error"), 500
