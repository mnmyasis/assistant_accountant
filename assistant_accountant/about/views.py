from django.shortcuts import render


def index(request):
    context = {}
    return render(request, 'about/index.html', context)
