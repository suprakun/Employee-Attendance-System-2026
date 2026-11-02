function openModal(id){const el=document.getElementById(id);if(el)el.classList.add('show')}
function closeModal(id){const el=document.getElementById(id);if(el)el.classList.remove('show')}
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-backdrop.show').forEach(m=>m.classList.remove('show'))});
