# -*- coding: utf-8 -*-
"""
    wakatime.models.polls
    ~~~~~~~~~~~~~~~~~~~~~

    GitHub polls.
"""


from datetime import datetime

from sqlalchemy.inspection import inspect

from wakatime import app, json, r, utils
from wakatime.constants import (
    USER_AUDIT_LOG_EVENT_POLL_CREATED,
    USER_AUDIT_LOG_EVENT_POLL_DELETED,
)

from .base import UUID, Model, cached_method, db


class Poll(Model):
    id = db.Column(UUID(), primary_key=True, default=utils.uuid74)
    user_id = db.Column(UUID(), db.ForeignKey("user.id"), nullable=False, index=True)
    _choices = db.Column(db.String(), nullable=False, default="[]")
    _votes = db.relationship("PollVote", backref="poll", lazy="dynamic")
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)

    _default_fields = [
        "choices",
        "votes",
    ]

    def __init__(self, *args, **kwargs):
        super(Poll, self).__init__(**kwargs)
        session = inspect(self).session or db.session
        data = {"poll_id": self.id}
        session.add(UserAuditLog(event=USER_AUDIT_LOG_EVENT_POLL_CREATED, event_data=data))

    @property
    def choices_sorted(self):
        c = self.choices
        c.sort(key=lambda x: (-self.votes.get(x, 0), x.lower()))
        return c

    @property
    def choices(self):
        return json.loads(self._choices or "[]")

    @choices.setter
    def choices(self, val):
        self._choices = json.dumps(val)

    @property
    @cached_method
    def votes(self):
        votes = {}
        choices = json.loads(self._choices or "[]")
        for choice in choices:
            votes[choice] = self._votes.filter_by(choice=choice).count()
        return votes

    @property
    def votes_history(self):
        return self._votes.order_by(PollVote.created_at.desc()).all()

    @property
    def num_votes(self):
        return self._votes.count()

    @property
    def last_voted_at(self):
        vote = self._votes.order_by(PollVote.created_at.desc()).first()
        if not vote:
            return None
        return vote.created_at

    def vote_for(self, choice):
        choices = set(self.choices)
        if choice not in choices:
            return
        created = PollVote._get_or_create(
            poll_id=self.id, user_id=app.current_user.id, choice=choice, defaults={"github_username": app.current_user._github_login}
        )[1]
        if created:
            db.session.commit()
            r.delete(f"poll-{self.id}")

    def remove_vote_for(self, choice):
        vote = self._votes.filter_by(choice=choice, user_id=app.current_user.id).first()
        if vote:
            db.session.delete(vote)
            db.session.commit()
            r.delete(f"poll-{self.id}")

    def current_user_voted_for(self, choice):
        return bool(self._votes.filter_by(choice=choice, user_id=app.current_user.id).first())

    def delete(self):
        session = inspect(self).session or db.session
        data = {"poll_id": self.id}
        session.add(UserAuditLog(event=USER_AUDIT_LOG_EVENT_POLL_DELETED, event_data=data))
        self._votes.delete()
        session.delete(self)
        session.commit()
        r.delete(f"poll-{data['poll_id']}")

    @property
    def title(self):
        return utils.shorten(", ".join(self.choices))

    @property
    def image_url(self):
        host = "http://localhost:5000" if app.config["DEV"] else "https://wakatime.com"
        return f"{host}/polls/{self.id}.png"

    @property
    def url(self):
        host = "http://localhost:5000" if app.config["DEV"] else "https://wakatime.com"
        return f"{host}/polls/{self.id}"

    @property
    def markdown(self):
        return f"[![poll]({self.image_url})]({self.url})"


class PollVote(Model):
    id = db.Column(UUID(), primary_key=True, default=utils.uuid74)
    poll_id = db.Column(UUID(), db.ForeignKey("poll.id"), nullable=False, index=True)
    user_id = db.Column(UUID(), db.ForeignKey("user.id"), nullable=False, index=True)
    choice = db.Column(db.String(), nullable=False)
    github_username = db.Column(db.String(), nullable=False, default=lambda: app.current_user.github_username)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "poll_id", "choice"),)

    _default_fields = [
        "choice",
        "github_username",
        "created_at",
    ]

    @property
    def github_username_url(self):
        return f"https://github.com/{self.github_username}"


from .users import UserAuditLog
