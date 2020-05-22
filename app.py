from flask import (
    Flask,
    render_template,
    url_for,
    request,
    redirect,
)

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import (
    validators,
    TextAreaField,
    StringField,
)
import re

from flask_bootstrap import Bootstrap
import random
import uuid
from sqlalchemy_utils import UUIDType

app = Flask(__name__)
app.config.from_pyfile("config.py")

Bootstrap(app)

# Create database connection object
db = SQLAlchemy(app)

class Hat(db.Model):
    id = db.Column(UUIDType(), primary_key=True)
    stage = db.Column(db.String(255))
    words = db.relationship("Word", backref="hat")

    def __str__(self):
        return f"<Hat {self.id}>"

    @property
    def words_inside(self):
        return [w for w in self.words if not w.guessed]


class Word(db.Model):
    id = db.Column(UUIDType(), primary_key=True)
    text = db.Column(db.String(255))
    guessed = db.Column(db.Boolean, default=False)
    hat_id = db.Column(UUIDType(), db.ForeignKey('hat.id'))

    def __str__(self):
        return f"<Word {self.id}: {self.word}> in {self.hat}"


class AddWordsForm(FlaskForm):
    words = TextAreaField(
        "Enter words, delimited by spaces, commas or newlines",
        validators=[validators.DataRequired()],
    )

class EnterIdForm(FlaskForm):
    hat_id = StringField("Hat ID", description="Hat ID")
    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        hat = Hat.query.get(self.hat_id.data)

        if not hat:
            self.name.errors.append("Hat not found")
            return False
        return True


@app.route("/make")
def handler_make():
    hat = Hat(stage="init", id=uuid.uuid4())
    db.session.add(hat)
    db.session.commit()
    return redirect(url_for("handler_addwords", hat_id=hat.id))

@app.route("/addwords/<hat_id>", methods=('POST','GET'))
def handler_addwords(hat_id):
    hat = Hat.query.get_or_404(hat_id)
    if hat.stage != 'init':
        return redirect(url_for("handler_play", hat_id=hat.id))
    words = {w.text for w in hat.words}
    form = AddWordsForm()
    if request.method == "POST" and form.validate_on_submit():
        text = form.words.data
        text_words = re.split(r"[ ,\n\r]+", text)
        for text_word in text_words:
            text_word = text_word.strip()
            if text_word:
                if text_word not in words:
                    words.add(text_word)
                    word = Word(text=text_word,
                                hat=hat,
                                id=uuid.uuid4())
                    db.session.add(word)
        db.session.commit()
        form.words.data = ""

    return render_template("addwords.html",
                           form=form,
                           hat=hat)

@app.route("/start/<hat_id>", methods=("GET", "POST"))
def handler_start(hat_id):
    hat = Hat.query.get_or_404(hat_id)
    if request.method == "POST":
        if hat.stage == 'init':
            hat.stage = "play"
        db.session.commit()
        return redirect(url_for("handler_play", hat_id=hat.id))
    return render_template("start.html", hat=hat)

@app.route("/play/<hat_id>")
def handler_play(hat_id):
    hat = Hat.query.get_or_404(hat_id)
    if hat.stage == 'init':
        return redirect(url_for("handler_addwords",
                                hat_id=hat.id))
    elif not hat.words_inside:
        db.session.commit()
        return redirect(url_for("handler_gameover",
                                hat_id=hat.id))
    return render_template("play.html", hat=hat)

@app.route("/getword/<hat_id>")
def handler_getword(hat_id):
    hat = Hat.query.get_or_404(hat_id)
    if hat.stage == 'init':
        return redirect(url_for("handler_addwords", hat_id=hat.id))
    words = hat.words_inside
    if not hat.words_inside:
        return redirect(url_for("handler_gameover", hat_id=hat.id))
    word = random.choice(words)
    return render_template("getword.html", hat=hat, word=word)

@app.route("/removeword/<hat_id>/<word_id>", methods=("POST",))
def handler_removeword(hat_id, word_id):
    hat = Hat.query.get_or_404(hat_id)
    word = Word.query.get_or_404(word_id)
    if word in hat.words:
        word.guessed = True
        db.session.commit()
    return redirect(url_for("handler_play", hat_id=hat.id))

@app.route('/', methods=('POST', 'GET'))
def handler_homepage():
    form = EnterIdForm()
    if request.method == "POST" and form.validate_on_submit():
        return redirect(url_for("handler_play", hat_id=form.hat_id.data))
    return render_template("homepage.html", form=form)


@app.route("/gameover/<hat_id>")
def handler_gameover(hat_id):
    hat = Hat.query.get_or_404(hat_id)
    if hat.words_inside:
        return redirect(url_for("handler_play", hat_id=hat.id))
    return render_template("gameover.html")

if __name__ == "__main__":
    db.create_all()
    db.session.commit()
    app.run()
