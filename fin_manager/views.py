from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from fin_manager import models
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.views.generic import TemplateView
from .models import Account, Liability
from .forms import LiabilityForm
from django.views.generic.edit import FormView
from django.views.generic import ListView


# Create your views here.

# @login_required(login_url='/signin')

def home(request):
    return render(request, 'fin_manager/home.html', {'user': request.user})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in
            login(request, user)
            return redirect('home')  # Change 'home' to your desired URL
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


class ExpenseListView(FormView):
    template_name = 'expenses/expense_list.html'
    form_class = LiabilityForm
    success_url = '/expenses/'  # Update this with the correct URL

    def form_valid(self, form):
        # Retrieve the user's account
        account, _ = Account.objects.get_or_create(user=self.request.user)
        
        # Create a new liability instance and link it to the user's account
        liability = Liability(
            name=form.cleaned_data['name'],
            amount=form.cleaned_data['amount'],
            interest_rate=form.cleaned_data['interest_rate'],
            end_date=form.cleaned_data['end_date'],
            user=self.request.user
        )
        liability.save()
        account.liability_list.add(liability)
        return super().form_valid(form)
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Retrieve user's account data and related liabilities
        accounts = Account.objects.filter(user=user)
        print(accounts)
        # Create a dictionary to store expense data grouped by month
        expense_data = {}

        for account in accounts:
            liabilities = account.liability_list.all()
            for liability in liabilities:
                year_month = liability.end_date.strftime('%Y-%m')

                if year_month not in expense_data:
                    expense_data[year_month] = []

                expense_data[year_month].append({
                    'name': liability.name,
                    'amount': liability.amount,
                    'end_date': liability.end_date,
                })
        
        context['expense_data'] = expense_data
        return context

def dashboard(request):
    user = request.user

    account, _ = Account.objects.get_or_create(user=user)

    # Fetch all liabilities (expenses) related to this account
    liabilities = account.liability_list.all()

    # Calculate total expenses
    total_expenses = liabilities.aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate total income (Assuming income is stored in 'balance' field)
    total_income = account.balance  

    # Calculate remaining balance
    remaining_balance = total_income - total_expenses

    # Group expenses by category
    category_expenses = liabilities.values('name').annotate(total=Sum('amount'))

    # Format data for the chart
    expense_chart_data = {
        'labels': [item['name'] for item in category_expenses], 
        'values': [item['total'] for item in category_expenses]
    }

    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'remaining_balance': remaining_balance,
        'expense_chart_data': expense_chart_data,
        'liabilities': liabilities,
    }

    return render(request, 'fin_manager/dashboard.html', context)

@login_required(login_url='/accounts/login/')  # Redirect to login if not authenticated
def dashboard(request):
    user = request.user
    
    if not user.is_authenticated:
        return redirect('/accounts/login/')  # Redirect unauthenticated users

    accounts = Account.objects.filter(user=user)

    # Fetch total expenses grouped by category
    expense_data = accounts.values('liability_list__name').annotate(total=Sum('liability_list__amount'))

    # Prepare data for Chart.js
    expense_chart_data = {
        "labels": [entry["liability_list__name"] for entry in expense_data],
        "values": [entry["total"] for entry in expense_data]
    }

    return render(request, 'fin_manager/dashboard.html', {'expense_chart_data': expense_chart_data})