from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django.core.mail import send_mail
from daily_fresh import settings
from django.http import HttpResponse
from user.models import User
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from celery_tasks import tasks
import re


# Create your views here.

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html', {})

    def post(self, request):
        """进行注册处理"""
        # 接受数据
        user_name = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据校验

        if not all([user_name, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 进行业务处理: 进行用户注册
        try:
            user = User.objects.get(username=user_name)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 用户注册-- 学习的时候出了bug(注意是User.objects中自带的方法）
        user = User.objects.create_user(user_name, email, password)
        user.is_active = 0
        user.save()

        # 激活链接中需要包含用户的身份信息  /user/active/1
        # 加密用户的身份信息， 生成激活token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info).decode('utf8')
        print(token)

        # 发邮件
        subject = '天天生鲜欢迎信息'
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]
        html_message = '<h1>%s ，欢迎您成为天天生鲜会员</h1>, 请点击下面链接激活您的账户<br> <a href="http://127.0.0.1:8000/user/active/%s">点击激活</a>' % (
        user_name, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        tasks.send_register_active_mail.delay(email, user_name, token)

        # 返回应答，跳转到首页
        # return redirect(reverse('goods:index'))
        return HttpResponse("OK")

class ActiveView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']

            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as s:
            return HttpResponse("激活链接已经过期失效")


class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIE.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username, password]):
            return render(request, 'index.html', {'errmsg': '数据不完整'})

        # django内置的身份验证函数
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名和密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)

                # 获取登录后所要跳转的地址
                next_url = request.GET.get('next', reverse('goods:index'))

                # 跳转到next_url
                response = redirect(next_url) # HttpResponseRedict

                # 判断是否需要记住用户名
                remember = request.POST.get('remember')

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('user_name', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('user_name')

                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '请激活用户'})

        else:
            # 用户名和密码错误
            return render(request, 'login.html', {'errmsg':'用户名和密码错误'})



