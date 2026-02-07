import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
def ping(request):
    """
    Простой ping endpoint для проверки работоспособности сервера
    """
    return Response({'status': 'ok', 'message': 'pong'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def j108_proxy(request, path=''):
    """
    Прокси-endpoint для API j108.net
    
    Проксирует запросы авторизованных пользователей к j108.net API,
    добавляя X-API-Key заголовок автоматически.
    
    Использование:
        GET/POST/PUT/PATCH/DELETE /api/j108/<path>/
        
    Пример:
        GET /api/j108/chart/ -> https://j108.net/api/chart/
        POST /api/j108/calculate/ -> https://j108.net/api/calculate/
    """
    # Формируем URL к j108.net API
    j108_url = f"{settings.J108_API_URL}/{path}"
    
    # Добавляем query параметры если есть
    if request.query_params:
        query_string = request.query_params.urlencode()
        j108_url = f"{j108_url}?{query_string}"
    
    # Заголовки для запроса к j108
    headers = {
        'X-API-Key': settings.J108_API_KEY,
        'Content-Type': 'application/json',
    }
    
    try:
        # Выполняем запрос в зависимости от метода
        if request.method == 'GET':
            response = requests.get(j108_url, headers=headers, timeout=30)
        elif request.method == 'POST':
            response = requests.post(j108_url, headers=headers, json=request.data, timeout=30)
        elif request.method == 'PUT':
            response = requests.put(j108_url, headers=headers, json=request.data, timeout=30)
        elif request.method == 'PATCH':
            response = requests.patch(j108_url, headers=headers, json=request.data, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(j108_url, headers=headers, timeout=30)
        else:
            return Response(
                {'error': 'Method not allowed'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        # Возвращаем ответ от j108.net
        try:
            response_data = response.json()
        except ValueError:
            response_data = {'raw': response.text}
        
        return Response(response_data, status=response.status_code)
        
    except requests.Timeout:
        return Response(
            {'error': 'Request to j108.net timed out'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.RequestException as e:
        return Response(
            {'error': f'Error connecting to j108.net: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
