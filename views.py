from django.contrib.auth.hashers import make_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Task, UserAnswer
from .serializers import TaskSerializer
import logging
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import render
from datetime import datetime, date
import pytz
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
import json


User = get_user_model()
logger = logging.getLogger(__name__)



# Регистрация пользователя
class register(APIView):
    def post(self, request):
        data = request.data
        email = data.get('email')

        if User.objects.filter(email=email).exists():
            return Response({"message": "Пользователь с таким email уже существует"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            last_name = data.get('lastName'),
            first_name = data.get('firstName'),
            middle_name = data.get('middleName'),
            last_login = datetime.now(pytz.timezone("Europe/Moscow")),
            email = data.get('email'),
            password = data.get('password'),
            settlement = data.get('settlement'),
            institution_type = data.get('institutionType'),
            institution_name = data.get('institutionName'),
            region = data.get('region'),
            grade = data.get('grade'),
            telegram = data.get('telegram'))
        user.set_password(data.get('password'))  # Безопасное шифрование пароля
        user.save()

        # Создаем токен
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Пользователь успешно зарегистрирован",
            "token": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)
    def get(self, request):
        return render(request, 'index.html')



# Вход в систему
class login(APIView):

    def post(self, request):
        # Получаем данные из тела запроса
        data = request.data
        email = data.get('email')
        password = data.get('password')

        # Проверяем наличие email и пароля
        if not email or not password:
            return Response({"message": "Email и пароль обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем пользователя по email
        user = get_object_or_404(User, email=email)

        # Проверяем пароль
        if not user.check_password(password):
            return Response({"message": "Неверный пароль"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user) # генерируем рефреш токен
        refresh['userId'] = user.id  # добавляем userId в рефреш токен
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        # Возвращаем оба токена на фронт и там их сохраняем в куку
        response = Response(data, status=status.HTTP_200_OK)
        return response

    def get(self, request):
        return render(request, 'index.html')



# Вход в профиль
class profile(APIView):
    def get(self, request):
        try:
            user = request.user  # Получаем текущего пользователя из токена
            if not user or not user.is_authenticated:
                cookie_header = request.headers.get('Cookie')
                # Парсим куку
                cookies = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in cookie_header.split('; ')}
                access_token = cookies.get('access_token')
                token = AccessToken(access_token)
                user = User.objects.get(id=token['userId'])
                print(token['userId'])
                if not user or not user.is_authenticated:
                    return Response({'message': 'Пользователь не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
            data = {
                "lastName": user.last_name,
                "firstName": user.first_name,
                "middleName": user.middle_name,
                "institutionName": user.institution_name,
            }
            print('Данные профиля:', data)
            user.last_login = str(datetime.now(pytz.timezone("Europe/Moscow")))[:-16]
            user.save()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as error:
            print('Ошибка при получении профиля:', error)
            return Response({'message': 'Ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Просмотр олимпиады
class olympiad_view(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info("Запрос на получение данных об олимпиаде")
        logger.info(f"Данные пользователя из токена: {request.user}")

        try:
            # Данные об олимпиаде
            olympiad_data = {
                'status': 'registered',
                'date': '8-9 февраля 2025 года',
                'startDate': f'{days_until_feb_8_2025_moscow()}',
                'duration': '2 дня',
            }
            logger.info(f"Данные об олимпиаде: {olympiad_data}")
            return Response(olympiad_data)
        except Exception as error:
            logger.error(f"Ошибка при получении данных об олимпиаде: {error}")
            return Response({"message": "Ошибка сервера"}, status=500)



# Получение всех заданий
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tasks(request):
    tasks = Task.objects.all()
    print(f"Tasks fetched: {tasks}")
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)



# Получение ответа 1
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_answers_view(request, userId):

    try:
        user_answers = UserAnswer.objects.filter(user_id=userId)
        data = []
        for ua in user_answers:
            data.append({
                "id": ua.id,
                "userId": ua.user_id,
                "taskId": ua.task_id,
                "answer": ua.answer,
                "isCorrect": ua.is_correct,
                "pointsEarned": ua.points_earned,
            })

        return Response(data, status=status.HTTP_200_OK)
    except Exception as error:
        print("Ошибка при получении ответов пользователя:", error)
        return Response({"message": "Ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Получение ответа 2
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_answer(request):
    user_id = request.query_params.get('userId')
    task_id = request.query_params.get('taskId')
    try:
        if not user_id or not task_id:
            return Response(
                {"message": "Необходимо указать userId и taskId."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_answer = UserAnswer.objects.filter(use_id=user_id, task_id=task_id).first()
        if not user_answer:
            return Response(
                {"answer": "", "isSubmitted": False},
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "answer": user_answer.answer,
                "isSubmitted": True,
            },
            status=status.HTTP_200_OK
        )

    except Exception as error:
        print("Ошибка при получении ответа пользователя:", error)
        return Response(
            {"message": "Ошибка сервера"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# Отправка ответа на задание
class submit_answer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        data = json.loads(request.body)
        # Извлекаем данные
        user_id = data.get("userId")
        task_id = data.get("taskId")
        answer = data.get("answer")
        user = get_object_or_404(User, id=user_id)

        if not task_id or not answer:
            return Response({"message": "Необходимо указать taskId и answer."}, status=400)

        # Предположим, что taskId = Task.custom_id
        task = Task.objects.filter(id=task_id.strip()).first()
        if not task:
            return Response({"message": "Задание не найдено"}, status=404)

        # Ищем существующий ответ:
        user_answer_qs = UserAnswer.objects.filter(user=user, task=task)
        existing_answer = user_answer_qs.first()

        # Логика проверки ответа
        # Приводим к нижнему регистру, убираем пробелы
        normalized_user_answer = answer.strip().lower()
        normalized_correct_answer = (task.correct_answer or "").strip().lower()

        is_correct = (normalized_user_answer == normalized_correct_answer)
        points_earned = task.points if is_correct else 0
        # --- ЛОГИКА ДЛЯ первой части ---
        if task.type == 'test':
            if existing_answer:
                # обновляем ответ
                previous_points = existing_answer.points_earned

                existing_answer.answer = answer
                existing_answer.is_correct = is_correct
                existing_answer.points_earned = points_earned
                moscow_now = datetime.now(pytz.timezone("Europe/Moscow"))
                existing_answer.time_answer = moscow_now
                existing_answer.save()

                # обновляем баллы
                user.total_points += (points_earned - previous_points)
                user.save()

            else:
                # Создаем новый ответ
                new_answer = UserAnswer(
                    user=user,
                    task=task,
                    answer=answer,
                    is_correct=is_correct,
                    points_earned=points_earned
                )
                new_answer.save()

                # Обновляем общие баллы
                user.total_points += points_earned
                user.save()

            # Возвращаем результат без информации о правильности ответа
            return Response({"message": "Ответ сохранен"}, status=200)

        # --- ЛОГИКА ДЛЯ второй части ---
        if existing_answer:
            # Если ответ уже существует и он правильный
            if existing_answer.is_correct:
                return Response({"message": "Вы уже отправили правильный ответ."}, status=400)

            # Если ответ неправильный, обновляем
            prev_points = existing_answer.points_earned
            existing_answer.answer = answer
            existing_answer.is_correct = is_correct
            existing_answer.points_earned = points_earned
            moscow_now = datetime.now(pytz.timezone("Europe/Moscow"))
            existing_answer.time_answer = moscow_now
            existing_answer.save()

            user.total_points += (points_earned - prev_points)
            user.save()

        else:
            # Если ответа нет, создаем новый
            new_answer = UserAnswer(
                user=user,
                task=task,
                answer=answer,
                is_correct=is_correct,
                points_earned=points_earned
            )
            new_answer.save()

            user.total_points += points_earned
            user.save()

        return Response({"isCorrect": is_correct, "pointsEarned": points_earned}, status=200)



# Проверка на доступность олимпиады
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_olympiad(request):
    try:
        user = request.user
        user_id = user.id
        # Точно так же возвращаем true
        isOlympiadAvailable = is_after_feb_8_2025_moscow()
        if user_id in (1, 4):
            isOlympiadAvailable = True

        return Response({"isAvailable": isOlympiadAvailable}, status=status.HTTP_200_OK)
    except Exception as error:
        print("Ошибка при проверке доступности олимпиады:", error)
        return Response({"message": "Ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Пересылка на реакт
def index(request):
    return render(request, 'index.html')



# Вспомогательно
# 1
def is_after_feb_8_2025_moscow():
    moscow_tz = pytz.timezone("Europe/Moscow")
    moscow_now = datetime.now(moscow_tz).date()
    target_date = date(2025, 2, 8)
    return moscow_now >= target_date
# 2
def days_until_feb_8_2025_moscow():
    moscow_tz = pytz.timezone("Europe/Moscow")
    moscow_now = datetime.now(moscow_tz).date()
    target_date = date(2025, 2, 8)
    remaining_days = (target_date - moscow_now).days

    if target_date == moscow_now:
        return "Олимпиада уже началась"
    elif moscow_now == date(2025, 2, 10) or remaining_days < 0:
        return "Олимпиада завершена"

    if 11 <= remaining_days % 100 <= 19:
        return f"{remaining_days} дней"
    elif remaining_days % 10 == 1:
        return f"{remaining_days} день"
    elif 2 <= remaining_days % 10 <= 4:
        return f"{remaining_days} дня"
    else:
        return f"{remaining_days} дней"

# --- The end... ---



# Пока не реализовано, но работает через перехватчик 401 на фронте
class RefreshTokenView(APIView):
    def post(self, request):
        try:
            cookies = request.COOKIES
            refresh_token = cookies.get("refresh_token")

            if not refresh_token:
                return Response({"message": "Refresh token отсутствует"}, status=401)

            # Создаём новый `access_token`
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            response = Response({"message": "Токен обновлён"})
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=False,
                samesite="None",
                path="/",
            )
            return response

        except Exception as e:
            return Response({"message": "Неверный или просроченный refresh token"}, status=401)
