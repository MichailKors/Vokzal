import os
import pickle
import datetime
from dataclasses import dataclass, field
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'central-station-secret-key'
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'railway_data.dat')


@dataclass
class User:
    id: int
    name: str = ''
    surname: str = ''
    email: str = ''
    password: str = ''
    phone: str = ''
    time: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class Ticket:
    id: int
    user_id: int
    where_from: str = ''
    to: str = ''
    date_of_trip: str = ''
    name: str = ''
    surname: str = ''
    train: str = 'TRAIN'
    time: str = '9:00'
    price: int = 3500


@dataclass
class Route:
    id: int
    user_id: int
    where_from: str = ''
    to: str = ''


class Book:
    """Класс сохраняет логику и файловое хранение из консольной лабораторной работы."""
    def __init__(self):
        self.users = {}
        self.tickets = {}
        self.routes = {}
        self.maxID = 0

    def next_id(self):
        self.maxID += 1
        return self.maxID

    def add_user(self, name, surname, email, password):
        user = User(self.next_id(), name=name, surname=surname, email=email, password=password)
        self.users[user.id] = user
        return user

    def change_user(self, user_id, **kwargs):
        user = self.users.get(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        return user

    def delete_user(self, user_id):
        self.users.pop(user_id, None)
        self.tickets = {tid: t for tid, t in self.tickets.items() if t.user_id != user_id}
        self.routes = {rid: r for rid, r in self.routes.items() if r.user_id != user_id}

    def find_user_by_email(self, email):
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    def add_ticket(self, user_id, where_from, to, date_of_trip, name, surname):
        ticket = Ticket(self.next_id(), user_id, where_from, to, date_of_trip, name, surname)
        self.tickets[ticket.id] = ticket
        return ticket

    def user_tickets(self, user_id):
        return [t for t in self.tickets.values() if t.user_id == user_id]

    def delete_ticket(self, ticket_id, user_id):
        ticket = self.tickets.get(ticket_id)
        if ticket and ticket.user_id == user_id:
            del self.tickets[ticket_id]
            return True
        return False

    def add_route(self, user_id, where_from, to):
        for route in self.routes.values():
            if route.user_id == user_id and route.where_from == where_from and route.to == to:
                return route
        route = Route(self.next_id(), user_id, where_from, to)
        self.routes[route.id] = route
        return route

    def user_routes(self, user_id):
        return [r for r in self.routes.values() if r.user_id == user_id]

    def delete_route(self, route_id, user_id):
        route = self.routes.get(route_id)
        if route and route.user_id == user_id:
            del self.routes[route_id]
            return True
        return False

    def store(self, filename=DATA_FILE):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            pickle.dump((self.maxID, self.users, self.tickets, self.routes), f)

    def load(self, filename=DATA_FILE):
        if not os.path.exists(filename):
            return
        with open(filename, 'rb') as f:
            self.maxID, self.users, self.tickets, self.routes = pickle.load(f)


book = Book()
book.load()


def save():
    book.store()


def current_user():
    user_id = session.get('user_id')
    return book.users.get(user_id) if user_id else None


@app.context_processor
def inject_user():
    return {'current_user': current_user()}


@app.route('/')
def index():
    trains = [
        {'number': '723А', 'route': 'Москва - Санкт-Петербург', 'time': '14:30', 'platform': '3', 'status': 'Посадка', 'kind': 'boarding'},
        {'number': '054Ч', 'route': 'Москва - Казань', 'time': '15:15', 'platform': '5', 'status': 'По расписанию', 'kind': 'ok'},
        {'number': '001А', 'route': 'Москва - Сочи', 'time': '16:00', 'platform': '2', 'status': 'Задержан', 'kind': 'late'},
        {'number': '102М', 'route': 'Москва - Нижний Новгород', 'time': '16:45', 'platform': '1', 'status': 'По расписанию', 'kind': 'ok'},
        {'number': '086В', 'route': 'Москва - Воронеж', 'time': '17:20', 'platform': '4', 'status': 'По расписанию', 'kind': 'ok'},
    ]
    return render_template('index.html', trains=trains, active='home')


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    tab = request.args.get('tab', 'login')
    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if not email or '@' not in email or '.' not in email:
            flash('Введите корректный Email', 'error')
            return redirect(url_for('auth', tab=action or tab))
        if action == 'register':
            if book.find_user_by_email(email):
                flash('Пользователь с такой почтой уже существует', 'error')
                return redirect(url_for('auth', tab='register'))
            user = book.add_user('Иван', 'Иванов', email, password)
            session['user_id'] = user.id
            save()
            return redirect(url_for('profile'))
        user = book.find_user_by_email(email)
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Неверный email или пароль', 'error')
    return render_template('auth.html', active='profile', tab=tab)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = current_user()
    if not user:
        return redirect(url_for('auth'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip() or user.name
        surname = request.form.get('surname', '').strip() or user.surname
        email = request.form.get('email', '').strip() or user.email
        phone = request.form.get('phone', '').strip() or user.phone
        if '@' not in email or '.' not in email:
            flash('Введите корректную электронную почту', 'error')
            return redirect(url_for('profile'))
        book.change_user(user.id, name=name, surname=surname, email=email, phone=phone)
        save()
        flash('Профиль обновлен', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', active='profile')


@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        user = current_user()
        if not user:
            return render_template(
                'buy.html',
                active='buy',
                auth_required=True,
                auth_message='Уважаемый пользователь! Сначала нужно войти или зарегистрироваться.'
            )
        where_from = request.form.get('where_from', '').strip()
        to = request.form.get('to', '').strip()
        date = request.form.get('date_of_trip', '').strip()
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        if request.form.get('save_route'):
            book.add_route(user.id, where_from, to)
            save()
            return redirect(url_for('routes'))
        book.add_ticket(user.id, where_from, to, date, name, surname)
        save()
        return redirect(url_for('my_tickets'))
    return render_template('buy.html', active='buy')


@app.route('/routes')
def routes():
    user = current_user()
    user_routes = book.user_routes(user.id) if user else []
    return render_template('routes.html', routes=user_routes, active='routes')


@app.post('/routes/<int:route_id>/delete')
def delete_route(route_id):
    user = current_user()
    if user:
        book.delete_route(route_id, user.id)
        save()
    return redirect(url_for('routes'))


@app.route('/tickets')
def my_tickets():
    user = current_user()
    tickets = book.user_tickets(user.id) if user else []
    return render_template('tickets.html', tickets=tickets, active='tickets')


@app.route('/return')
def return_ticket():
    user = current_user()
    tickets = book.user_tickets(user.id) if user else []
    return render_template('return.html', tickets=tickets, active='return')


@app.post('/tickets/<int:ticket_id>/delete')
def delete_ticket(ticket_id):
    user = current_user()
    if user:
        book.delete_ticket(ticket_id, user.id)
        save()
    return redirect(url_for('return_ticket'))


if __name__ == '__main__':
    app.run(debug=True)
