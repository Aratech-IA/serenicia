const trElementTotalTable = document.querySelectorAll(".total_restock")
const userInputs = document.querySelectorAll('.app6-user-input')
nappies = []

const bagsToRestockInitialisation = () => {
    for (i = 0; i < trElementTotalTable.length; i += 1){
        let nappiesToRestock = 0
        for (j = 0; j < userInputs.length; j += 1) {
            // check if the protection name are the same line by line for the 2 tables
            if (trElementTotalTable[i].children[0].textContent === userInputs[j].parentNode.parentNode.children[1].children[0].value) {
                nappiesToRestock += parseInt(userInputs[j].value)
            }
        }
        let nappiesPerBag = trElementTotalTable[i].children[2].textContent
        nappies.push({
            "name": trElementTotalTable[i].children[0].textContent,
            "nappiesToRestock": nappiesToRestock,
            "nappiesPerBag": nappiesPerBag,
            "bagsToRestock": Math.ceil(nappiesToRestock / nappiesPerBag),
        })
    }
}

bagsToRestockInitialisation()

const bagsToRestock = () => {
    for (i = 0; i < trElementTotalTable.length; i += 1){
        let newNappiesToRestock = 0
        for (j = 0; j < userInputs.length; j += 1) {
            // check if the protection name are the same line by line for the 2 tables
            if (trElementTotalTable[i].children[0].textContent === userInputs[j].parentNode.parentNode.children[1].children[0].value) {
                console.log(userInputs[j].value !== "")
                // prevent case NaN
                if (userInputs[j].value !== "") {
                    newNappiesToRestock += parseInt(userInputs[j].value)
                }
            }
        }
        let nappy = nappies.filter(nappy => nappy.name === trElementTotalTable[i].children[0].textContent)
        nappy[0].nappiesToRestock = newNappiesToRestock

        newBagsToRestock = Math.ceil(newNappiesToRestock / nappy[0].nappiesPerBag)
        trElementTotalTable[i].children[1].textContent = newBagsToRestock
    }
}

for (i = 0; i < userInputs.length; i += 1){
    userInputs[i].addEventListener('input', function(){
        bagsToRestock()
    })
}

