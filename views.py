from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Task, UserAnswer
from .serializers import UserSerializer, TaskSerializer, UserAnswerSerializer
import logging
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.shortcuts import render
from datetime import datetime, date
import pytz
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken

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

        # Генерируем токен
        refresh = RefreshToken.for_user(user)
        refresh['userId'] = user.id  # Добавляем user_id в токен
        # Возвращаем токен клиенту
        return Response({"token": str(refresh.access_token)}, status=status.HTTP_200_OK)

    def get(self, request):
        return render(request, 'index.html')


@csrf_exempt
# Просто добавляем декоратор напрямую
@api_view(['GET'])
def profile(request):
    try:
        print(request.headers)
        user = request.user  # Получаем текущего пользователя из токена
        if not user or not user.is_authenticated:
            return Response({'message': 'Пользователь не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)

        data = {
            "lastName": user.last_name,
            "firstName": user.first_name,
            "middleName": user.middle_name,
            "institutionName": user.institution_name,
        }
        print('Данные профиля:', data)
        return Response(data, status=status.HTTP_200_OK)
    except Exception as error:
        print('Ошибка при получении профиля:', error)
        return Response({'message': 'Ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class olympiad_view(APIView):
    permission_classes = [IsAuthenticated]  # Проверка аутентификации

    def get(self, request):
        logger.info("Запрос на получение данных об олимпиаде")  # Логируем начало запроса
        logger.info(f"Данные пользователя из токена: {request.user}")  # Логируем данные пользователя

        try:
            # Данные об олимпиаде
            olympiad_data = {
                'status': 'registered',
                'date': '8-9 февраля 2025 года',
                'startDate': f'{days_until_feb_8_2025_moscow()}',
                'duration': '2 дня',
            }
            logger.info(f"Данные об олимпиаде: {olympiad_data}")  # Логируем данные об олимпиаде
            return Response(olympiad_data)
        except Exception as error:
            logger.error(f"Ошибка при получении данных об олимпиаде: {error}")  # Логируем ошибку
            return Response({"message": "Ошибка сервера"}, status=500)

# Получение всех заданий
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tasks(request):
    tasks = Task.objects.all()  # Или добавьте фильтрацию, если нужно
    print(f"Tasks fetched: {tasks}")  # Логирование в консоль
    serializer = TaskSerializer(tasks, many=True)
    return Response(serializer.data)

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



# Отправка ответа на задание
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request):

    data = request.data
    user = request.user

    # 1. Извлекаем taskId, answer
    task_id = data.get('taskId')
    answer = data.get('answer')

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

    # --- ЛОГИКА ДЛЯ type == 'test' ---
    if task.type == 'test':
        if existing_answer:
            # обновляем ответ
            previous_points = existing_answer.points_earned

            existing_answer.answer = answer
            existing_answer.is_correct = is_correct
            existing_answer.points_earned = points_earned
            existing_answer.save()

            # обновляем баллы (предположим, что у нас user.profile.total_points)
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

    # --- ЛОГИКА ДЛЯ второй части (type in ['web', 'forensic', 'archive', ...]) ---
    if existing_answer:
        # Если ответ уже существует и он правильный
        if existing_answer.is_correct:
            return Response({"message": "Вы уже отправили правильный ответ."}, status=400)

        # Если ответ неправильный, обновляем
        prev_points = existing_answer.points_earned
        existing_answer.answer = answer
        existing_answer.is_correct = is_correct
        existing_answer.points_earned = points_earned
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_olympiad(request):
    try:
        user = request.user
        user_id = user.id
        # Точно так же возвращаем true
        isOlympiadAvailable = is_after_feb_8_2025_moscow()
        if user_id in (1, 2):
            isOlympiadAvailable = True

        return Response({"isAvailable": isOlympiadAvailable}, status=status.HTTP_200_OK)
    except Exception as error:
        print("Ошибка при проверке доступности олимпиады:", error)
        return Response({"message": "Ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def is_after_feb_8_2025_moscow():
    moscow_tz = pytz.timezone("Europe/Moscow")
    moscow_now = datetime.now(moscow_tz).date()
    target_date = date(2025, 2, 8)
    return moscow_now >= target_date

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


def index(request):
    return render(request, 'index.html')

