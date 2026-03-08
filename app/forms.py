from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms import ValidationError
from flask_wtf.file import FileField, FileAllowed
from flask import session
from app import translate
from app.models import Ticket, User


def tr(en_text, es_text):
    return es_text if session.get('lang', 'en') == 'es' else en_text


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username.label.text = tr('Username', 'Usuario')
        self.password.label.text = tr('Password', 'Contraseña')
        self.remember_me.label.text = tr('Remember Me', 'Recordarme')
        self.submit.label.text = tr('Sign In', 'Entrar')


class TicketForm(FlaskForm):
    creator_name = StringField('Your name', validators=[DataRequired(), Length(max=120)])
    title = StringField('Title', validators=[DataRequired(), Length(max=140)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[(c,c) for c in ['Red','Impresoras','Software','Hardware']])
    priority = SelectField('Priority', choices=[(p,p) for p in ['Baja','Media','Alta','Crítica']])
    attachment = FileField('Attachment', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'pdf', 'txt', 'doc', 'docx', 'xlsx', 'csv'], 'Invalid file type')])
    submit = SubmitField('Create Ticket')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator_name.label.text = tr('Your name', 'Tu nombre')
        self.title.label.text = tr('Title', 'Título')
        self.description.label.text = tr('Description', 'Descripción')
        self.category.label.text = tr('Category', 'Categoría')
        self.priority.label.text = tr('Priority', 'Prioridad')
        self.attachment.label.text = tr('Attachment', 'Adjunto')
        self.submit.label.text = tr('Create Ticket', 'Crear ticket')
        self.category.choices = [(c, c) for c in Ticket.categories()]
        self.priority.choices = [(p, p) for p in Ticket.priorities()]
        if session.get('lang', 'en') == 'en':
            self.category.choices = [
                (c, translate(c, 'en')) for c in Ticket.categories()
            ]
            self.priority.choices = [
                (p, translate(p, 'en')) for p in Ticket.priorities()
            ]


class TicketUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[(s,s) for s in ['Abierto','En proceso','Esperando usuario','Cerrado']])
    # allow empty submission even if no choices available
    technician = SelectField('Assign to', coerce=int, choices=[], validate_choice=False)  # filled in view
    submit = SubmitField('Update Ticket')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.label.text = tr('Status', 'Estado')
        self.technician.label.text = tr('Assign to', 'Asignar a')
        self.submit.label.text = tr('Update Ticket', 'Actualizar ticket')
        if session.get('lang', 'en') == 'en':
            self.status.choices = [
                ('Abierto', 'Open'),
                ('En proceso', 'In progress'),
                ('Esperando usuario', 'Waiting user'),
                ('Cerrado', 'Closed')
            ]


class TicketCommentForm(FlaskForm):
    message = TextAreaField('Comment', validators=[DataRequired(), Length(min=2, max=2000)])
    submit_comment = SubmitField('Add comment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message.label.text = tr('Comment', 'Comentario')
        self.submit_comment.label.text = tr('Add comment', 'Agregar comentario')


class UserRoleForm(FlaskForm):
    role = SelectField('Role', choices=[(r, r.capitalize()) for r in ['user', 'technician', 'admin']])
    is_active = BooleanField('Active')
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role.label.text = tr('Role', 'Rol')
        self.is_active.label.text = tr('Active', 'Activo')
        self.submit.label.text = tr('Save', 'Guardar')


def company_email(form, field):
    # enforce one of the approved corporate domains
    allowed = ['@eie-puj.com', '@eie-lrm.com', '@bppclub.com']
    if not any(field.data.endswith(d) for d in allowed):
        raise ValidationError(
            tr('Email must belong to one of: ', 'El correo debe pertenecer a: ') + ', '.join(allowed)
        )


class NewUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), company_email])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[(r, r.capitalize()) for r in ['user', 'technician', 'admin']], default='user')
    submit = SubmitField('Create User')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username.label.text = tr('Username', 'Usuario')
        self.email.label.text = tr('Email', 'Correo')
        self.password.label.text = tr('Password', 'Contraseña')
        self.password2.label.text = tr('Repeat Password', 'Repetir contraseña')
        self.role.label.text = tr('Role', 'Rol')
        self.submit.label.text = tr('Create User', 'Crear usuario')

    def validate_username(self, field):
        username = (field.data or '').strip()
        if User.query.filter_by(username=username).first() is not None:
            raise ValidationError(tr('Username already exists', 'El usuario ya existe'))

    def validate_email(self, field):
        email = (field.data or '').strip().lower()
        if User.query.filter_by(email=email).first() is not None:
            raise ValidationError(tr('Email already exists', 'El correo ya existe'))


class TicketOptionForm(FlaskForm):
    option_type = SelectField('Type', choices=[('category', 'Category'), ('priority', 'Priority')], validators=[DataRequired()])
    value = StringField('Value', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Add')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_type.label.text = tr('Type', 'Tipo')
        self.value.label.text = tr('Value', 'Valor')
        self.submit.label.text = tr('Add', 'Agregar')
        if session.get('lang', 'en') == 'es':
            self.option_type.choices = [('category', 'Categoría'), ('priority', 'Prioridad')]

    def validate_value(self, field):
        field.data = field.data.strip()
        if not field.data:
            raise ValidationError(tr('Value is required', 'El valor es obligatorio'))


class ForcePasswordChangeForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Update Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_password.label.text = tr('New Password', 'Nueva contraseña')
        self.confirm_password.label.text = tr('Confirm Password', 'Confirmar contraseña')
        self.submit.label.text = tr('Update Password', 'Actualizar contraseña')


class AdminResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_password.label.text = tr('New Password', 'Nueva contraseña')
        self.confirm_password.label.text = tr('Confirm Password', 'Confirmar contraseña')
        self.submit.label.text = tr('Reset Password', 'Restablecer contraseña')
