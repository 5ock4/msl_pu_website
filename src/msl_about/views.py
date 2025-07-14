from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
import numpy as np
import pandas as pd

from msl_results.models import Result
from .models import SeasonRounds, RoundsPage
from util.models import CategoryChoices


def store_to_results_model(results: pd.DataFrame, round_obj):
    """
    Store results DataFrame to Result model in database
    """
    from msl_about.models import Team
    
    for _, row in results.iterrows():
        try:
            team_name = row['team']
            category_excel = row['category_excel']
            
            # Try to find existing team by name and category
            try:
                team = Team.objects.get(name=team_name, category=category_excel)
            except Team.DoesNotExist:
                team = None
            
            # Process LP value
            lp_value = 0.0
            ranking_def = 'U'  # Default value
            
            if pd.notna(row['lp']):
                try:
                    lp_value = float(row['lp'])
                except (ValueError, TypeError):
                    # If conversion fails, it's text - store in ranking_def
                    ranking_def = str(row['lp'])[:2]  # Limit to 2 characters as per model
            
            # Process PP value
            pp_value = 0.0
            if pd.notna(row['pp']):
                try:
                    pp_value = float(row['pp'])
                except (ValueError, TypeError):
                    # If conversion fails, it's text - store in ranking_def
                    ranking_def = str(row['pp'])[:2]  # Limit to 2 characters as per model
            
            # Create or update the result
            result, created = Result.objects.get_or_create(
                team_excel=team_name,
                round=round_obj,
                category_excel=category_excel,
                defaults={
                    'team': team,
                    'competitors_borrowed': int(row['competitors_borrowed']) if pd.notna(row['competitors_borrowed']) else 0,
                    'lp': lp_value,
                    'pp': pp_value,
                    'ranking_def': ranking_def,
                    'points': int(row['points_excel']) if pd.notna(row['points_excel']) else 0,
                }
            )
            
            # If the result already exists, update it
            if not created:
                result.team = team
                result.competitors_borrowed = int(row['competitors_borrowed']) if pd.notna(row['competitors_borrowed']) else 0
                result.lp = lp_value
                result.pp = pp_value
                result.ranking_def = ranking_def
                result.points = int(row['points_excel']) if pd.notna(row['points_excel']) else 0
                result.save()
                
        except Exception as e:
            print(f'Error saving result for team {row["team"]} in category {row["category_excel"]}: {str(e)}')
            continue

def read_results_file(results_file):
    results = pd.read_excel(
            results_file,
            header=2,
            usecols=['LIGOVÉ BODY', 'SDH', 'TEAM', 'LIGA -1   NELIGOVÝ - 0', 'PŮJČENÝ ZÁVODNÍK M-1, Ž-1,2, SG-1',
                     '1-M,  2-Ž, 3-35', 'LEVÝ PROUD', 'PRAVÝ PROUD']
        ) \
        .dropna(subset=['SDH']) \
        .rename(columns={
            'LIGOVÉ BODY': 'points_excel',
            'SDH': 'sdh',
            'TEAM': 'team',
            'LIGA -1   NELIGOVÝ - 0': 'msl',
            'PŮJČENÝ ZÁVODNÍK M-1, Ž-1,2, SG-1': 'competitors_borrowed',
            '1-M,  2-Ž, 3-35': 'category_excel',
            'LEVÝ PROUD': 'lp',
            'PRAVÝ PROUD': 'pp'
        })
    results['team'] = np.where(
        (results['team'].notna()) & (results['team'] != 'A'), 
        results['sdh'] + ' ' + results['team'], 
        results['sdh']
    )
    results = results.drop(columns=['sdh'])
    
    # Map category numeric values to readable text
    category_mapping = {
        1: CategoryChoices.MUZI.value,
        2: CategoryChoices.ZENY.value,
        3: CategoryChoices.VETERANI.value
    }
    results['category_excel'] = results['category_excel'].map(category_mapping)
    # Select only teams part of MSL
    results = results[results['msl'] == 1]

    return results

def is_wagtail_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.username == 'RadaMSL')

@user_passes_test(is_wagtail_admin)
def upload_results(request, round_id):
    round_obj = get_object_or_404(SeasonRounds, id=round_id)
    
    if request.method == 'POST' and request.FILES.get('results_file'):
        results_file = request.FILES['results_file']
        
        results: pd.DataFrame = read_results_file(results_file)

        # Store results to database
        store_to_results_model(results, round_obj)

        # Mark results as ready
        round_obj.save()

        messages.success(request, f'Výsledky pro kolo {round_obj.round} úspěšně vloženy!')

    # Redirect back to the rounds page
    try:
        rounds_page = RoundsPage.objects.live().first()
        if rounds_page:
            return redirect(rounds_page.url)
    except:
        pass
    
    # Fallback redirect
    return redirect('/')
