const one_mo = 1048576;

function updateButtonText(){
        var span = document.getElementById("checked-count")
        var count = document.querySelectorAll(".recipientsmessage:checked").length
        span.textContent = count
        var btn = span.parentElement
        if(count > 0){
            btn.classList.remove('disabled')
            btn.classList.remove('btn-perso')
            btn.classList.add('btn-perso')
        }else{
            btn.classList.add('disabled')
            btn.classList.add('btn-perso')
            btn.classList.remove('btn-perso')
        };
    };

function toggleSingleUser(user, type, is_checked){
    if(type == 'CC'){
        document.getElementById('user' + user).checked = false;
        document.getElementById('user' + user + 'CCI').checked = false;
        document.getElementById('user' + user + 'CC').checked = is_checked;
    }else if(type == 'CCI'){
        document.getElementById('user' + user).checked = false;
        document.getElementById('user' + user + 'CC').checked = false;
        document.getElementById('user' + user + 'CCI').checked = is_checked;
    }else{
        try{
            document.getElementById('user' + user + 'CCI').checked = false;
            document.getElementById('user' + user + 'CC').checked = false;
        }catch(error){};
        document.getElementById('user' + user).checked = is_checked;
    };
    updateButtonText();
};

function toggleRelatedUsers(users_list, type, is_checked){
    var ids = JSON.parse(users_list);
    if(type == 'CC'){
        for(var i=0; i<ids.length; i++){
            try{
                document.getElementById('user' + ids[i]).checked = false;
                document.getElementById('user' + ids[i] + 'CCI').checked = false;
                document.getElementById('user' + ids[i] + 'CC').checked = is_checked;
            } catch (error) {};
        };
    }else if(type == 'CCI'){
        for(var i=0; i<ids.length; i++){
            try{
                document.getElementById('user' + ids[i]).checked = false;
                document.getElementById('user' + ids[i] + 'CC').checked = false;
                document.getElementById('user' + ids[i] + 'CCI').checked = is_checked;
            } catch (error) {};
        };
    }else{
        for(var i=0; i<ids.length; i++){
            try{
                document.getElementById('user' + ids[i]).checked = is_checked;
                document.getElementById('user' + ids[i] + 'CC').checked = false;
                document.getElementById('user' + ids[i] + 'CCI').checked = false;
            } catch (error) {};
        };
    };
    updateButtonText();
};

function toggleSenderOnly(users_list, sender, is_checked){
    var ids = JSON.parse(users_list);
    for(var i=0; i<ids.length; i++){
        try{
            document.getElementById('user' + ids[i]).checked = false;
        } catch (error) {};
    };
    document.getElementById('user' + sender).checked = is_checked;
    updateButtonText();
};
