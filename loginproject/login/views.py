from django.shortcuts import render
from django.shortcuts import redirect
from . import models
from django import forms
from login import forms
from django.conf import settings
from django.views.generic import View
from functools import wraps
from django.utils.decorators import method_decorator
# Create your views here.
import hashlib
import datetime

def hash_code(s, salt='mysite'):  # 加点盐
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())  # update方法只接收bytes类型
    return h.hexdigest()

def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user,)
    return code


def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives

    subject = '来自事务管理系统的注册确认邮件'

    text_content = '''感谢注册事务管理系统，专注于个人事务的管理！\
                    如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''

    html_content = '''
                    <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>事务管理系统</a>，\
                    专注于个人事务的管理！</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>
                    '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)

    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

# session认证装饰器
def login_check(func):
    @wraps(func)
    def wrapper(request):
        if not request.session.get('is_login', None):
            return redirect("/login/")
        else:
            return func(request)
    return wrapper


# CBV模式

class IndexView(View):
    '''
    首页
    '''
    def get(self,request):
        return render(request, 'login/index.html')


class RegisterView(View):
    '''
    注册
    '''
    def get(self,request):
        register_form = forms.RegisterForm(request.POST)
        return render(request, 'login/register.html', {'message': '','register_form':register_form})

    def post(self,request):
        register_form = forms.RegisterForm(request.POST)
        if register_form.is_valid():  # 获取数据
            username = request.POST.get('username','')
            password1 = request.POST.get('password1','')
            password2 = request.POST.get('password2','')
            email = request.POST.get('email','')
            sex = request.POST.get('sex','')
            if password1 != password2:  # 判断两次密码是否相同
                message = "两次输入的密码不同！"
                return render(request, 'login/register.html', {'message': message, 'register_form': register_form})
            else:
                same_name_user = models.User.objects.filter(name=username)
                same_email_user = models.User.objects.filter(email=email)
                if same_name_user:  # 用户名唯一
                    message = '用户已经存在，请重新选择用户名！'
                    return render(request, 'login/register.html', {'message': message, 'register_form': register_form})
                elif same_email_user:  # 邮箱地址唯一
                    message = '该邮箱地址已被注册，请使用别的邮箱！'
                    return render(request, 'login/register.html', {'message': message, 'register_form': register_form})

                else:
                    # 当一切都OK的情况下，创建新用户

                    new_user = models.User()
                    new_user.name = username
                    new_user.password = hash_code(password1)  # 使用哈希加密密码
                    new_user.email = email
                    new_user.sex = sex
                    new_user.save()

                    code = make_confirm_string(new_user)
                    send_email(email, code)
                    message = '请前往注册邮箱，进行邮件确认！'
                    return render(request, 'login/confirm.html', {'message': message})  # 跳转到等待邮件确认页面。


class LoginView(View):
    '''
    登录
    '''
    def get(self,request):
        login_form = forms.UserForm(request.POST)
        return render(request,'login/login.html',{'login_form':login_form})


    def post(self,request):
        login_form = forms.UserForm(request.POST)
        message = "请检查填写的内容！"
        if login_form.is_valid():
            # username = login_form.cleaned_data['username']
            # password = login_form.cleaned_data['password']
            username = request.POST.get('username','')
            password = request.POST.get('password','')

            try:
                user = models.User.objects.get(name=username)
                if not user.has_confirmed:
                    message = "该用户还未通过邮件确认！"
                    return render(request, 'login/login.html', {'message': message,'login_form':login_form})
                if user.password == hash_code(password):  # 哈希值和数据库内的值进行比对
                    # 记录会话状态
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    return redirect('/index/')
                else:
                    message = "密码不正确！"
            except:
                message = "用户不存在！"
        return render(request, 'login/login.html', {'message': message,'login_form':login_form})


class LogoutView(View):
    '''
    退出
    '''
    def get(self,request):
        if not request.session.get('is_login', None):
            return redirect("/index/")
        request.session.flush()
        # 或者使用下面的方法
        # del request.session['is_login']
        # del request.session['user_id']
        # del request.session['user_name']
        return redirect("/index/")


class UserConfirmView(View):
    '''
    邮箱激活认证
    '''
    def get(self,request):
        code = request.GET.get('code', None)

        try:
            confirm = models.ConfirmString.objects.get(code=code)
        except:
            message = '无效的确认请求!'
            return render(request, 'login/confirm.html', {'message': message})

        c_time = confirm.c_time
        now = datetime.datetime.now()
        if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
            confirm.user.delete()
            message = '您的邮件已经过期！请重新注册!'
            return render(request, 'login/confirm.html', {'message': message})
        else:
            confirm.user.has_confirmed = True
            confirm.user.save()
            confirm.delete()
            message = '感谢确认，请使用账户登录！'
            login_form = forms.UserForm(request.POST)
            return render(request, 'login/login.html', {'message': message, 'login_form': login_form})


class ContentView(View):

    @method_decorator(login_check)
    def get(self,request):
        message = '验证气泡显示'
        return render(request, 'content.html', {'message': message})


# FBV模式
# def index(request):
#     return render(request,'login/index.html')


# def login(request):
#     message=""
#     if request.session.get('is_login', None):
#         return redirect("/index/")
#     if request.method == "POST":
#         login_form = forms.UserForm(request.POST)
#         message = "请检查填写的内容！"
#         if login_form.is_valid():
#             username = login_form.cleaned_data['username']
#             password = login_form.cleaned_data['password']
#             try:
#                 user = models.User.objects.get(name=username)
#                 if not user.has_confirmed:
#                     message = "该用户还未通过邮件确认！"
#                     return render(request, 'login/login.html', {'message':message})
#                 if user.password == hash_code(password):  # 哈希值和数据库内的值进行比对
#                     #记录会话状态
#                     request.session['is_login'] = True
#                     request.session['user_id'] = user.id
#                     request.session['user_name'] = user.name
#                     return redirect('/index/')
#                 else:
#                     message = "密码不正确！"
#             except:
#                 message = "用户不存在！"
#         return render(request, 'login/login.html', {'message':message})
#
#     login_form = forms.UserForm()
#     return render(request, 'login/login.html', {'message':message, 'login_form':login_form})




# def register(request):
#     message = ""
#     if request.session.get('is_login', None):
#         # 登录状态不允许注册。
#         return redirect("/index/")
#     if request.method == "POST":
#         register_form = forms.RegisterForm(request.POST)
#         message = ""
#         if register_form.is_valid():  # 获取数据
#             username = register_form.cleaned_data['username']
#             password1 = register_form.cleaned_data['password1']
#             password2 = register_form.cleaned_data['password2']
#             email = register_form.cleaned_data['email']
#             sex = register_form.cleaned_data['sex']
#             if password1 != password2:  # 判断两次密码是否相同
#                 message = "两次输入的密码不同！"
#                 return render(request, 'login/register.html', {'message':message,'register_form':register_form})
#             else:
#                 same_name_user = models.User.objects.filter(name=username)
#                 same_email_user = models.User.objects.filter(email=email)
#                 if same_name_user:  # 用户名唯一
#                     message = '用户已经存在，请重新选择用户名！'
#                     return render(request, 'login/register.html', {'message':message,'register_form':register_form})
#                 elif same_email_user:  # 邮箱地址唯一
#                     message = '该邮箱地址已被注册，请使用别的邮箱！'
#                     return render(request, 'login/register.html', {'message':message,'register_form':register_form})
#
#                 else:
#                     # 当一切都OK的情况下，创建新用户
#
#                     new_user = models.User()
#                     new_user.name = username
#                     new_user.password = hash_code(password1)  # 使用哈希加密密码
#                     new_user.email = email
#                     new_user.sex = sex
#                     new_user.save()
#
#                     code = make_confirm_string(new_user)
#                     send_email(email, code)
#                     message = '请前往注册邮箱，进行邮件确认！'
#                     return render(request, 'login/confirm.html', {'message':message})  # 跳转到等待邮件确认页面。
#     register_form = forms.RegisterForm()
#     return render(request, 'login/register.html', {'message':message, 'register_form':register_form})


# def logout(request):
#     if not request.session.get('is_login', None):
#         # 如果本来就未登录，也就没有登出一说
#         return redirect("/index/")
#     #清除会话
#     request.session.flush()
#     # 或者使用下面的方法
#     # del request.session['is_login']
#     # del request.session['user_id']
#     # del request.session['user_name']
#     return redirect("/index/")

# def user_confirm(request):
#     code = request.GET.get('code', None)
#     message = ''
#
#     try:
#         confirm = models.ConfirmString.objects.get(code=code)
#     except:
#         message = '无效的确认请求!'
#         return render(request, 'login/confirm.html', {'message':message})
#
#     c_time = confirm.c_time
#     now = datetime.datetime.now()
#     if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
#         confirm.user.delete()
#         message = '您的邮件已经过期！请重新注册!'
#         return render(request, 'login/confirm.html', {'message':message})
#     else:
#         confirm.user.has_confirmed = True
#         confirm.user.save()
#         confirm.delete()
#         message = '感谢确认，请使用账户登录！'
#         login_form = forms.UserForm(request.POST)
#         return render(request, 'login/login.html', {'message':message,'login_form':login_form})


# def content(request):
#     if not request.session.get('is_login', None):
#         return redirect("/login/")
#     message = '验证气泡显示'
#     return render(request, 'content.html', {'message': message})