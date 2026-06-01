document.addEventListener("DOMContentLoaded", function () {
  const editorEl = document.getElementById("quill-editor");
  const hiddenInput = document.getElementById("body_html");
  if (editorEl && hiddenInput && window.Quill) {
    const quill = new Quill("#quill-editor", {
      theme: "snow",
      placeholder: "Escreva o texto aqui...",
      modules: {
        toolbar: [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline"],
          [{ list: "ordered" }, { list: "bullet" }],
          [{ align: [] }],  // <-- ADICIONE ESTA LINHA para alinhamento
          ["link", "blockquote", "code-block"],
          ["clean"]
        ]
      }
    });
    // Inicializa com HTML existente
    if (hiddenInput.value) {
      const temp = document.createElement("div");
      temp.innerHTML = hiddenInput.value;
      quill.clipboard.dangerouslyPasteHTML(temp.innerHTML);
    }
    // Antes de enviar o form, copia o HTML para o hidden input
    const form = editorEl.closest("form");
    if (form) {
      form.addEventListener("submit", function () {
        hiddenInput.value = editorEl.querySelector(".ql-editor").innerHTML;
      });
    }
  }
});