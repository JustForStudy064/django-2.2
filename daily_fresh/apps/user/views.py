from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django.core.mail import send_mail
from daily_fresh import settings
from django.http import HttpResponse
from user.models import User, Address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
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
        send_mail(subject, message, sender, receiver, html_message=html_message)
        # tasks.send_register_active_mail.delay(email, user_name, token)

        # 返回应答，跳转到首页
        return redirect(reverse('goods:index'))
        # return HttpResponse("OK")


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
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        # django内置的身份验证函数
        user = authenticate(username=username, password=password)
        # user = User.objects.get(username=username)
        # if password != user.password:
        #     user = None

        if user is not None:
            # 用户名和密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)

                # 获取登录后所要跳转的地址
                next_url = request.GET.get('next', reverse('goods:index'))

                # 跳转到next_url
                response = redirect(next_url)  # HttpResponseRedict

                # 判断是否需要记住用户名
                remember = request.POST.get('remember')

                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('user_name', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('user_name')

                return response
            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '请激活用户'})

        else:
            # 用户名和密码错误
            return render(request, 'login.html', {'errmsg': '用户名和密码错误'})


class LogoutView(View):
    """退出登陆"""

    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


# /user
class UserOrderView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'user_center_order.html', {'page': 'order'})


# /user/order
class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        address = Address.objects.get_default_address(user)

        # 使用模板
        return render(request, 'user_center_info.html', {'page': 'user', 'address': address, 'user': user})


# /user/address
class AddressView(LoginRequiredMixin, View):
    """用户中心页面"""

    def get(self, request):
        # 获取登录用户对应的User对象
        user = request.user

        address = Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='172.16.179.130', port='6379', db=9)

        con = get_redis_connection('default')

        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)

        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        context = {'page': 'address',
                   'address': address,
                   'goods_li': goods_li}

        # 使用模板
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'page': 'address', 'errmsg': '数据不完整'})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'page': 'address', 'errmsg': '手机格式不正确'})

        user = request.user

        address = Address.objects.get_default_address(user)

        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None

        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        # 返回应答， 刷新地址页面
        return redirect(reverse('user:address'))  # get 请求方式
