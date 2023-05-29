function addUserToMember(user_id){
        var base_card = document.getElementById('base-card');
        var new_card = base_card.cloneNode(true);
        new_card.classList.remove('d-none');
        new_card.id = 'card' + user_id;
        new_card.children[0].src = document.getElementById('photo' + user_id).value;
        new_card.children[1].children[0].textContent = document.getElementById('name' + user_id).textContent;
        new_card.children[1].children[1].textContent = document.getElementById('grp' + user_id).value;
        base_card.parentNode.appendChild(new_card);
    };


function activeRelatedUsers(users, is_checked, disable){
    let ids = JSON.parse(users);
    if(is_checked){
        for(var i=0; i<ids.length; i++){
            if(document.getElementById('card' + ids[i]) == null){
                addUserToMember(ids[i]);
            };
            document.getElementById('user' + ids[i]).checked = true;
            document.getElementById('user' + ids[i]).disabled = disable;
        };
    }else{
        for(var i=0; i<ids.length; i++){
            document.getElementById('card' + ids[i]).remove();
            document.getElementById('user' + ids[i]).checked = false;
            document.getElementById('user' + ids[i]).disabled = false;
        };
    };
};