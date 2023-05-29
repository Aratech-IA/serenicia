# from django.db import models
# from django.contrib.auth.models import User, Group
# from app1_base.models import Profile, Client, SubSector
# from app1_base.log import Logger
# from app4_ehpad_base.models import ProfileSerenicia, UserListIntermediate
# import math
# import time, json, logging
# import random
#
#
# # ---------------------------------------------SHUFFLE------------------------------------------------------------------
# def algo_shuffle(access):
#     if 'log_shuffle' not in globals():
#         global log_algo_shuffles
#         log_algo_shuffles = Logger('algo_shuffles', level=logging.ERROR).run()
#
#     log_algo_shuffles.debug(f"SHUFFLE access concerned: {access}")
#
#     users = User.objects.filter(groups__permissions__codename=access)
#     users = users.exclude(last_login__isnull=True).exclude(groups__permissions__codename="view_admin")
#     users = users.order_by('profileserenicia__entry_date')
#     residents_list = User.objects.filter(groups__permissions__codename='view_resident')
#     residents_list = residents_list.filter(profile__client__isnull=False)  # exclude resident without Client
#     residents_list = residents_list.exclude(profileserenicia__status="Deceased")
#     residents = residents_list.order_by('profile__client__sector',  # order by sector
#                                         'profile__client__room_number')  # then by room number
#     # list division
#     user_lists = list(users)
#     first_half = user_lists[:len(user_lists)//2]
#     second_half = user_lists[len(user_lists)//2:]
#     second_half.reverse()
#     final_list = []
#     if len(first_half) > len(second_half):
#         for i in range(len(second_half)):  # shortest
#             final_list.append([first_half[i], second_half[i]])
#         final_list.append([first_half[-1], ])  # longest
#     elif len(first_half) < len(second_half):
#         for i in range(len(first_half)):
#             final_list.append([first_half[i], second_half[i]])
#         final_list.append([second_half[-1], ])
#     else:
#         final_list.append(list(x) for x in zip(first_half, second_half))
#     users = final_list
#     # log_algo_shuffles.debug(f"FINAL LIST user: {users}")
#
#     for team in users:
#         for user in team:
#             for profile in user.profileserenicia.user_list.filter(
#                     user__groups__permissions__codename='view_resident'):
#                 inter = user.profileserenicia.userlistintermediate_set.get(profile=profile.id)
#                 if not inter.was_manual:
#                     user.profileserenicia.user_list.remove(profile.id)
#             if user.profileserenicia.user_list:
#                 log_algo_shuffles.debug(f"SHUFFLE user: {user}")
#                 for profile in user.profileserenicia.user_list.all():
#                     inter = UserListIntermediate.objects.filter(profile=profile)
#                     inter = inter.filter(profileserenicia__user=user)
#                     log_algo_shuffles.debug(f"SHUFFLE manual affectations: {profile.user.username} - {inter[0].id}")
#                 log_algo_shuffles.debug(f"----------------------------------------------------------")
#
#     r = len(residents) / len(users)
#     reste = len(residents) % len(users)
#
#     for team in users:
#         if reste > 0:
#             ratio = int(r)+1
#         else:
#             ratio = int(r)
#         while len(team[0].profileserenicia.user_list.filter(user__groups__permissions__codename='view_resident')) < ratio:
#             for user in team:
#                 log_algo_shuffles.debug(f"SHUFFLE user: {user}")
#                 user.profileserenicia.user_list.add(residents[0].profile.id)
#                 user_list_inter = user.profileserenicia.userlistintermediate_set.get(profile=residents[0].profile.id)
#                 user_list_inter.was_manual = False
#                 user_list_inter.save()
#                 user.profileserenicia.save()
#                 for profile in user.profileserenicia.user_list.all():
#                     inter = UserListIntermediate.objects.filter(profile=profile)
#                     inter = inter.filter(profileserenicia__user=user)
#                     log_algo_shuffles.debug(f"SHUFFLE final affectations: {profile.user.username} - {inter[0].id}")
#                 log_algo_shuffles.debug(f"----------------------------------------------------------")
#             residents = residents.exclude(id=residents[0].id)
#
#         reste -= 1
#
#
# def spread(x, y):
#     orga = []
#     r = y / x
#     reste = y % x
#     print(reste)
#     for n in range(x):
#         t = 0
#         orga.append(t)
#         if reste > 0:
#             ratio = int(r)+1
#         else:
#             ratio = int(r)
#         print(reste, ratio, y)
#         while t < ratio:
#             orga[n] += 1
#             y -= 1
#             t += 1
#         reste -= 1
#     print(orga, reste, r)
#     return orga
#
#
# def repar(x, y):
#     sous = x // 2
#     r1 = x - sous
#     r2 = sous
#     spread1 = spread(r1, y)
#     spread2 = spread(r2, y)
#     return spread1, spread2
