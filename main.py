from PdfScrapper import *

campi = PDFFinder().get_courses_profile_links()

for campus in campi:
    for course, pdf_path in campi[campus]:
        print(campus, course, pdf_path)
        if pdf_path[0] == "h":
            pass
        else:
            try:
                curso = PDFScapper.scrape(PDFFinder.url_base + pdf_path)
                curso.nome = course
                curso.perfil_curricular_dot().render(
                    "outputs/%s-%s" % (campus.replace(" ", ""), curso.nome.replace(" ", ""))
                )
            except:
                print('Erro com o PDF')
