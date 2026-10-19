import os
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")


def is_empty(stack):
    """Return True when the stack contains no items."""
    return len(stack) == 0


def len_stack(stack):
    """Return the number of items in a stack."""
    return len(stack)


@app.get("/")
def index():
    stack = session.get("stack", [])
    return render_template("index.html", stack=stack, stack_size=len_stack(stack))


@app.post("/push")
def push():
    value = request.form.get("value", "").strip()
    if not value:
        flash("Escribe un valor antes de agregarlo a la pila.", "warning")
        return redirect(url_for("index"))

    stack = session.get("stack", [])
    stack.append(value)
    session["stack"] = stack
    flash(f"Se agregó «{value}» a la pila.", "success")
    return redirect(url_for("index"))


@app.post("/pop")
def pop():
    stack = session.get("stack", [])
    if is_empty(stack):
        flash("La pila está vacía; no hay elementos que retirar.", "warning")
    else:
        value = stack.pop()
        session["stack"] = stack
        flash(f"Se retiró «{value}» de la pila.", "success")
    return redirect(url_for("index"))


@app.post("/peek")
def peek():
    stack = session.get("stack", [])
    if is_empty(stack):
        flash("La pila está vacía; no hay elemento superior.", "warning")
    else:
        flash(f"Elemento en la cima: «{stack[-1]}».", "info")
    return redirect(url_for("index"))


@app.post("/clear")
def clear():
    session["stack"] = []
    flash("La pila se vació correctamente.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
