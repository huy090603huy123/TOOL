function addSuffix() {
    fetch('/add-suffix', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({suffix: newSuffix.value})
    })
    .then(res=>res.json())
    .then(data=>{
        suffix.innerHTML = ""
        data.suffixes.forEach(s=>{
            let opt = document.createElement("option")
            opt.textContent = s
            suffix.appendChild(opt)
        })
        newSuffix.value = ""
    })
}

function start() {
    log.innerHTML = "⏳ Đang xử lý...\n"
    fetch('/process',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
            name: name.value,
            suffix: suffix.value
        })
    })
    .then(res=>res.json())
    .then(data=>{
        data.logs.forEach(l=>{
            log.innerHTML += l + "\n"
        })
    })
}
