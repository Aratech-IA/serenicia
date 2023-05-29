import base64
from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from app9_personnalized_project.forms import AddingRelation, AddingPerson, ModifyRelation, AddingEntente
from app9_personnalized_project.models import Person, Relation, Survey

import graphviz


def ordering_generation(family):
    list_person = Person.objects.filter(family=family, level_y__isnull=False).order_by('level_y')
    result = []
    for y_index in range(list_person.first().level_y, list_person.last().level_y + 1):
        result.append(list_person.filter(level_y=y_index).order_by('level_x', 'last_name', 'first_name'))
    return result


def build_ordered_list_generation(list_relations):
    lvl_y_min = list_relations.order_by('from_person__level_y').first().from_person.level_y
    lvl_y_max = list_relations.order_by('to_person__level_y').last().to_person.level_y
    result = []
    for lvl_y in range(lvl_y_min, lvl_y_max + 1):
        list_from_person = [relation.from_person for relation in list_relations.filter(from_person__level_y=lvl_y)]
        list_to_person = [relation.to_person for relation in list_relations.filter(to_person__level_y=lvl_y)]
        result.append(list(set(list_from_person) | set(list_to_person)))
    return result


def identify_resident(user):
    return Person.objects.get(last_name__iexact=user.last_name, first_name__iexact=user.first_name)


def get_relation_node_name(relation):
    if relation.from_person.id < relation.to_person.id:
        relation_node_name = f'{relation.from_person.id}-{relation.to_person.id}'
    else:
        relation_node_name = f'{relation.to_person.id}-{relation.from_person.id}'
    return relation_node_name


def get_graph(file_type, list_relations):
    resident = identify_resident(list_relations.first().from_person.family.user)
    shape = {0: 'box', 1: 'oval'}
    color = {'spouse': 'black:invis:black', 'ex_spouse': 'black:invis:black', 'partner': 'black', 'parent': 'black',
             'ex_partner': 'black', 'relative': 'black'}
    style = {'spouse': 'solid', 'partner': 'solid', 'parent': 'solid', 'ex_partner': 'dashed', 'ex_spouse': 'dashed',
             'relative': 'solid'}
    filled = {True: 'filled', False: None}
    dot = graphviz.Graph(format=file_type, engine='dot', edge_attr={'constraint': 'false'})
    existing_node = []
    existing_edge = []
    for generation in build_ordered_list_generation(list_relations):
        lvl = generation[0].level_y
        with dot.subgraph() as sub:
            sub.attr(rank='same', rankdir='TB')
            for person in generation:
                node_name = str(person.id)
                if person == resident:
                    sub.node(node_name, person.get_full_name(), shape=shape[person.gender], fillcolor='#93a9d2',
                             style='filled', color='#93a9d2')
                else:
                    sub.node(node_name, person.get_full_name(), shape=shape[person.gender],
                             style=filled[person.deceased])
                try:
                    for first_parent in list_relations.filter(from_person=person, type='parent', other=False):
                        second_parent = list_relations.filter(to_person=first_parent.to_person, type='parent', other=False).exclude(id=first_parent.id).get()
                        try:
                            tmp_rel = list_relations.get(Q(from_person=first_parent.from_person) | Q(from_person=second_parent.from_person),
                                                         Q(to_person=second_parent.from_person) | Q(to_person=first_parent.from_person), other=False)
                            relation_node_name = get_relation_node_name(tmp_rel)
                            if relation_node_name not in existing_node:
                                sub.node(name=relation_node_name, style='invis', height='0', width='0', label='')
                                existing_node.append(relation_node_name)
                        except ObjectDoesNotExist:
                            if first_parent.from_person.id < second_parent.from_person.id:
                                relation_node_name = f'{first_parent.from_person.id}-{second_parent.from_person.id}'
                            else:
                                relation_node_name = f'{second_parent.from_person.id}-{first_parent.from_person.id}'
                            if relation_node_name not in existing_node:
                                sub.node(name=relation_node_name, style='invis', height='0', width='0', label='')
                                existing_node.append(relation_node_name)
                                dot.edge(str(first_parent.from_person.id), relation_node_name)
                                dot.edge(str(second_parent.from_person.id), relation_node_name)
                except ObjectDoesNotExist:
                    pass
                existing_node.append(node_name)
            for relation in Relation.objects.filter(from_person__level_y=lvl, to_person__level_y=lvl, other=False):
                from_person_node, to_person_node = str(relation.from_person.id), str(relation.to_person.id)
                if from_person_node in existing_node and to_person_node in existing_node:
                    relation_node_name = get_relation_node_name(relation)
                    if relation_node_name in existing_node:
                        sub.edge(from_person_node, relation_node_name, style=style[relation.type],
                                 color=color[relation.type])
                        sub.edge(relation_node_name, to_person_node, style=style[relation.type],
                                 color=color[relation.type])
        for relation in list_relations.filter(type='parent', to_person__level_y=lvl).distinct('to_person'):
            parents = [str(rel.from_person.id) for rel in list_relations.filter(to_person=relation.to_person,
                                                                                type='parent',
                                                                                other=False).order_by('id')]
            parents_node_name = '-'.join([str(parent) for parent in parents])
            edge_name = parents_node_name + str(relation.to_person.id)
            for parent in parents:
                if parent in existing_node and edge_name not in existing_edge:
                    dot.edge(parents_node_name, str(relation.to_person.id), constraint='true')
                    existing_edge.append(edge_name)
    quality = {'good': 'green', 'bad': 'red', 'normal': 'black'}
    for relation in list_relations.filter(other=True):
        dot.edge(str(relation.from_person.id), str(relation.to_person.id), color=quality[relation.quality], dir='both', constraint='false')
    if file_type == 'pdf':
        buffer = BytesIO(initial_bytes=dot.pipe())
        return buffer
    elif file_type == 'png':
        with open(dot.render(), "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        return image_data


def get_graph_entente(list_relations):
    resident = identify_resident(list_relations.first().from_person.family.user)
    shape = {0: 'box', 1: 'oval'}
    color = {'good': 'green', 'bad': 'red', 'normal': 'black'}
    filled = {True: 'filled', False: None}
    dot = graphviz.Digraph(format='png', strict=True)
    from_person_id = str(resident.id)
    dot.node(from_person_id, resident.get_full_name(), shape=shape[resident.gender],
             style='filled', color='#93a9d2', fillcolor='#93a9d2')
    for relation in list_relations:
        if relation.from_person == resident:
            person = relation.to_person
        else:
            person = relation.from_person
        dot.node(str(person.id), person.get_full_name(), shape=shape[person.gender], style=filled[person.deceased])
        dot.edge(from_person_id, str(person.id), color=color[relation.quality], dir='both')
    with open(dot.render(), "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    return image_data


def create_from_profileserenicia(profileserenicia, resident):
    gender = {'Mr': 0, 'Mrs': 1, ' ': 0, 'M.': 0, 'Mme': 1, None: 0}
    return Person.objects.create(family=resident, last_name=profileserenicia.user.last_name,
                                 first_name=profileserenicia.user.first_name, level_y=0,
                                 gender=gender[profileserenicia.user.profile.civility],
                                 photo=profileserenicia.user.profile.photo,
                                 birth=profileserenicia.birth_date)


@login_required
@permission_required('app0_access.view_genosociogram')
def genosociogram(request, family):
    resident = ProfileSerenicia.objects.get(id=family)
    if resident.user.profile not in request.user.profileserenicia.user_list.all():
        return redirect('app9_personnalized_project index')
    context = {'family': family, 'survey': Survey.objects.filter(target=resident).last().id}
    fam_member = ProfileSerenicia.objects.filter(Q(user_list=resident.user.profile,
                                                   user__groups__permissions__codename='view_family') | Q(
        id=resident.id)).distinct('id')
    if not Person.objects.filter(family=resident).exists():
        result = []
        for profileserenicia in fam_member:
            person = create_from_profileserenicia(profileserenicia, resident)
            result.append(person)
        context['list_generation'] = [result]
        return render(request, 'app9_personnalized_project/genosociogram.html', context)
    for profileserenicia in fam_member:
        if not Person.objects.filter(last_name__iexact=profileserenicia.user.last_name,
                                     first_name__iexact=profileserenicia.user.first_name,
                                     family=resident).exists():
            create_from_profileserenicia(profileserenicia, resident)
    if Relation.objects.filter(from_person__family=resident).exists():
        context['preview'] = get_graph('png', Relation.objects.filter(from_person__family=resident))
    context['list_generation'] = ordering_generation(resident)
    return render(request, 'app9_personnalized_project/genosociogram.html', context)


@login_required
@permission_required('app0_access.view_genosociogram')
def person_details(request, family, person_id):
    context = {'family': family}
    person = Person.objects.get(id=person_id)
    context['person'] = person
    if request.method == 'POST':
        if request.POST.get('save_person'):
            person_form = AddingPerson(request.POST, request.FILES, instance=person)
            if person_form.is_valid():
                person_form.save()
            context.update({'category': _('Informations'), 'message': _('Changes have been saved')})
        elif request.POST.get('delete_person'):
            Person.objects.filter(id=request.POST.get('delete_person')).delete()
            return redirect('genosociogram', family=family)
        elif request.POST.get('new_rel') or request.POST.get('new_entente'):
            if request.POST.get('new_entente'):
                ctx_key = request.POST.get('new_entente')
                form = AddingEntente(request.POST, person=person)
            else:
                ctx_key = request.POST.get('new_rel')
                form = AddingRelation(request.POST, person=person)
            if form.is_valid():
                form.save(from_person=person)
                context.update({'category': _('Relationship'), 'message': _('Relationship succesfully added')})
            else:
                context[ctx_key] = {'form': form, 'from_person': person}
        else:
            if request.POST.get('modif_rel'):
                modif_rel = Relation.objects.get(id=request.POST.get('modif_rel'))
                context['modif_rel_modal'] = {'form': ModifyRelation(instance=modif_rel), 'relation': modif_rel}
            elif request.POST.get('update_rel'):
                update_rel = Relation.objects.get(id=request.POST.get('update_rel'))
                form = ModifyRelation(request.POST, instance=update_rel)
                if form.is_valid():
                    form.save()
                    context.update(
                        {'category': _('Relationship'), 'message': _('Relationship succesfully updated')})
            elif request.POST.get('delete_rel'):
                Relation.objects.filter(id=request.POST.get('delete_rel')).delete()
                context.update({'category': _('Relationship'), 'message': _('Relationship succesfully deleted')})
    else:
        if request.META.get('HTTP_REFERER'):
            relation = [value for value in request.META.get('HTTP_REFERER').split('/')
                        if value in ['entente', 'relation']]
            if relation:
                relation = relation[0]
                initial = {'to_person': Person.objects.filter(family=family).last()}
                tmp_data = {'entente': {'key': 'new_entente',
                                        'data': {'form': AddingEntente(person=person, initial=initial),
                                                 'from_person': person}},
                            'relation': {'key': 'new_rel',
                                         'data': {'form': AddingRelation(person=person, initial=initial),
                                                  'from_person': person}}}
                context[tmp_data[relation]['key']] = tmp_data[relation]['data']
    relations = Relation.objects.filter(Q(from_person=person) | Q(to_person=person))
    if relations.filter(other=True).exists():
        context['preview'] = get_graph_entente(relations.filter(other=True))
    context['relations'] = relations
    context['person_form'] = AddingPerson(instance=person)
    return render(request, 'app9_personnalized_project/person_details.html', context)


@login_required
@permission_required('app0_access.view_genosociogram')
def create_person(request, family, from_person, relation):
    form = AddingPerson(request.POST, request.FILES)
    if form.is_valid():
        person = form.save(commit=False)
        person.family = ProfileSerenicia.objects.get(id=family)
        person.save()
        return redirect('person details', family=family, person_id=from_person)
    return render(request, 'app9_personnalized_project/create_person.html', {'form': form, 'family': family, 'from_person': from_person})


@login_required
@permission_required('app0_access.view_genosociogram')
def download_family(request, family):
    fam_trad = _('family')
    geno_trad = _('genosociogram')
    fam_name = Person.objects.filter(family__id=family).first().family.user.last_name.lower()
    return FileResponse(get_graph('pdf', Relation.objects.filter(from_person__family__id=family)),
                        filename=f'{geno_trad}-{fam_trad}-{fam_name}.pdf')

