const edit = document.querySelector('#edit-course');
document.querySelectorAll('input[name="selected_course"]').forEach(radio => {
  radio.addEventListener('change', () => {
    edit.disabled = false;
    document.querySelectorAll('tbody tr').forEach(row => row.classList.remove('selected'));
    radio.closest('tr').classList.add('selected');
  });
});
edit?.addEventListener('click', () => {
  const selected = document.querySelector('input[name="selected_course"]:checked');
  if (selected) window.location.assign(selected.value);
});

