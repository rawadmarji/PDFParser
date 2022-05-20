#Import Libraries
import fitz
import os,json,uuid,string
from PIL import Image
from io import BytesIO
import pandas as pd
import re


#ENCODING = 'utf8'
ENCODING = 'ascii'

def sortPageBlocks(page_blocks):
    """
    Sort the page blocks in ascending vertical order then in ascending horizontal order
    """
    blocks = []
    for b in page_blocks:
        # x coordinate in pixels
        x0 = str(int(b["bbox"][0] + 0.99999)).rjust(4,"0")
        # y coordinate in pixels
        y0 = str(int(b["bbox"][1] + 0.99999)).rjust(4, "0")
        sortage_key = y0 + x0
        blocks.append([sortage_key,b])
    blocks.sort(key=lambda x: x[0])
    #Return a list of sorted blocks
    return [b[1] for b in blocks]

def sortBlockLines(block_lines):
    """
    Sort the block lines in ascending vertical order.
    """
    lines = []
    for l in block_lines:
        y0 = str(int(l["bbox"][1] + 0.99999)).rjust(4,"0")
        lines.append([y0,l])
    lines.sort(key=lambda x: x[0])
    #Return a list of sorted lines in block
    return [l[1] for l in lines]

def sortLineSpans(line_spans):
    """
    Sort the spans of a line in an ascending horizontal direction.
    """
    spans = []
    for s in line_spans:
        x0 = str(int(s["bbox"][1] + 0.99999)).rjust(4,"0")
        spans.append([x0,s])
    spans.sort(key=lambda x: x[0])
    return [s[1] for s in spans]

def get_document_title(pdf_content):
    doc_title_bloc  = -1
    doc_title = None

    for pg, page_content in pdf_content.items():
        if int(pg) == 0:
           for bloc_idx,b in page_content['Blocs'].items():
               if b['type'] == 0:
                  for line_idx, l in enumerate(sortBlockLines(b["lines"])):
                      #print(f'Page: {pg} - Bloc: {bloc_idx} - Line: {line_idx}') # - {l}
                      for span_idx,s in enumerate(sortLineSpans(l["spans"])):
                          #print(f'Span: {span_idx} - s: {s}')
                          if doc_title_bloc == -1:
                             if s['flags'] == 20 \
                                and s['font']== 'Arial-BoldMT':
                                #print('Document Title=',s['text'])
                                doc_title_bloc = bloc_idx
                                doc_title = s['text']
                                page_content['Blocs'][bloc_idx]['DocumentTitle'] = doc_title
    return doc_title_bloc, doc_title


def find_starting_number(s):
    result = -1
    if s[0].isdigit():
       result = re.search(r'\d+\.',s)
       if result is None:
          return -1
       else:
          result = int((result.group(0))[:-1])
          #print('result', result)
    return result

def detect_next_starting_step(pdf_content,start_bloc_idx,max_block_id):
    """
    Detect next any line starting with a number and .
    """
    step = {}
    for pg, page_content in pdf_content.items():
      for bloc_idx,b in page_content['Blocs'].items():
        #print('Block Index',bloc_idx , 'Start Bloc', start_bloc)
        if bloc_idx != max_block_id and bloc_idx > start_bloc_idx and b['type'] == 0:
           for line_idx, l in enumerate(sortBlockLines(b["lines"])):
               #print(f'Page: {pg} - Bloc: {bloc_idx} - Line: {line_idx} - {l}')
               for span_idx,s in enumerate(sortLineSpans(l["spans"])):
                   #print('Step detected**', span_idx, s)
                   if span_idx == 0 \
                      and 'text' in s \
                      and len(s['text']) > 0 \
                      and find_starting_number(s['text']) > 0:
                      stepID = find_starting_number(s['text'])
                      print("pg,bloc_idx,line_idx,span_idx,stepID,s",pg,bloc_idx,line_idx,span_idx,stepID,s)
                      step["page"] = pg
                      step["bloc_idx"] = bloc_idx
                      step["line_idx"] = line_idx
                      step["span_idx"] = span_idx
                      step["ID"]       = stepID
                      step["span"]     = s
                      return step

def detect_next_step(pdf_content,max_block_id,step):
    """
    Detect next any line starting with a number and .
    """
    next_step = {}
    for pg, page_content in pdf_content.items():
      for bloc_idx,b in page_content['Blocs'].items():
        if bloc_idx != max_block_id and bloc_idx > int(step["bloc_idx"]) and b['type'] == 0:
           for line_idx, l in enumerate(sortBlockLines(b["lines"])):
               #print(f'Page: {pg} - Bloc: {bloc_idx} - Line: {line_idx} - {l}')
               for span_idx,s in enumerate(sortLineSpans(l["spans"])):
                   #print('Step detected**', span_idx, s)
                   if span_idx == 0 \
                      and 'text' in s \
                      and len((s['text']).strip()) > 0 \
                      and find_starting_number(s['text']) > 0\
                      and int(s['origin'][0]) <= int(step["span"]["origin"][0]):
                      stepID = find_starting_number(s['text'])
                      print("Next step pg,bloc_idx,line_idx,span_idx,stepID,s",pg,bloc_idx,line_idx,span_idx,stepID,s)
                      next_step["page"] = pg
                      next_step["bloc_idx"] = bloc_idx
                      next_step["line_idx"] = line_idx
                      next_step["span_idx"] = span_idx
                      next_step["ID"]       = stepID
                      next_step["span"]     = s
                      return next_step


def get_title(pdf_content,step):
    title = ""
    for pg, page_content in pdf_content.items():
        for bloc_idx,b in page_content['Blocs'].items():
            if bloc_idx == step["bloc_idx"] and b['type'] == 0:
               for line_idx, l in enumerate(sortBlockLines(b["lines"])):
                   for span_idx, s in enumerate(sortLineSpans(l["spans"])):
                        if 'text' in s \
                           and len(s['text']) > 0:
                                #and find_starting_number(s['text']) > 0 \
                                #and int(s['origin'][0]) > int(step["span"]["origin"][0]):
                           if title.endswith(" ") or s["text"].startswith(" "):
                              title += s["text"]
                           else:
                              title += " " + s["text"]
    for x in string.punctuation:
        if title.strip().endswith(x):
           return title
    return None

def get_description(pdf_content,step):
    description = ""
    for pg, page_content in pdf_content.items():
        for bloc_idx,b in page_content['Blocs'].items():
            if bloc_idx > step["bloc_idx"] and b['type'] == 0:
               for line_idx, l in enumerate(sortBlockLines(b["lines"])):
                   #print(f'{line_idx},{l}')
                   for span_idx, s in enumerate(sortLineSpans(l["spans"])):
                       if span_idx == 0 \
                          and 'text' in s \
                          and len((s['text']).strip()) > 0 \
                          and find_starting_number(s['text']) > 0 \
                          and int(s['origin'][0]) > int(step["span"]["origin"][0]):
                          return description

                       if 'text' in s \
                          and len((s['text']).strip()) > 0:
                            if description.endswith(" ") or s["text"].startswith(" "):
                              description += s["text"]
                            else:
                              description += " " + s["text"]
    return description


def get_next_substep(pdf_content,max_block_id,step,starting_bloc_idx):
    substep = {}
    for pg, page_content in pdf_content.items():
      for bloc_idx,b in page_content['Blocs'].items():
        if bloc_idx < max_block_id and bloc_idx > starting_bloc_idx and b['type'] == 0:
           for line_idx, l in enumerate(sortBlockLines(b["lines"])):
               for span_idx,s in enumerate(sortLineSpans(l["spans"])):
                   if span_idx == 0 \
                      and 'text' in s \
                      and len(s['text']) > 0 \
                      and find_starting_number(s['text']) > 0 \
                      and int(s['origin'][0]) > int(step["span"]["origin"][0]):
                      substepID = find_starting_number(s['text'])
                      print("Substep pg,bloc_idx,line_idx,span_idx,stepID,s",pg,bloc_idx,line_idx,span_idx,substepID,s)
                      substep["page"] = pg
                      substep["bloc_idx"] = bloc_idx
                      substep["line_idx"] = line_idx
                      substep["span_idx"] = span_idx
                      substep["ID"]       = substepID
                      substep["span"]     = s
                      return substep
    return substep

def get_section_header(pdf_content,start_bloc_idx,max_block_id,step):
    section = {}
    for pg, page_content in pdf_content.items():
      for bloc_idx,b in page_content['Blocs'].items():
        #print('Block Index',bloc_idx , 'Start Bloc', start_bloc_idx,'step_bloc_idx',step["bloc_idx"] ,step["span"]["origin"][0])
        if bloc_idx != max_block_id \
           and bloc_idx > start_bloc_idx \
           and bloc_idx < int(step["bloc_idx"]) \
           and b['type'] == 0:
            for line_idx, l in enumerate(sortBlockLines(b["lines"])):
               #print(f'Page: {pg} - Bloc: {bloc_idx} - Line: {line_idx} - {l}')
                for span_idx, s in enumerate(sortLineSpans(l["spans"])):
                    if span_idx == 0 \
                       and s['flags'] == 20 \
                       and s['font'] == 'Arial-BoldMT' \
                       and int(s['origin'][0]) < int(step["span"]["origin"][0]) \
                       and s['text'] not in 'NOTE: ':
                       #and int(s['bbox'][0]) < 100
                       section["name"] = s['text']
                       section["page"] = pg
                       section["bloc_idx"] = bloc_idx
                       #print("Section",section)
    return section


def get_next_section(pdf_content,start_bloc_idx,max_block_id):
    section_start_bloc = -1
    section_end_bloc   = -1
    section = {}

    for pg, page_content in pdf_content.items():
      for bloc_idx,b in page_content['Blocs'].items():
        #print('Block Index',bloc_idx , 'Start Bloc', start_bloc)
        if bloc_idx != max_block_id and bloc_idx >= start_bloc_idx and b['type'] == 0:
           for line_idx, l in enumerate(sortBlockLines(b["lines"])):
               print(f'Page: {pg} - Bloc: {bloc_idx} - Line: {line_idx} - {l}')
               for span_idx,s in enumerate(sortLineSpans(l["spans"])):
                   if s['flags'] == 20 \
                      and s['font'] == 'Arial-BoldMT' \
                      and s['text'] not in 'NOTE: '\
                      and int(s['bbox'][0]) < 100:

                      if section_start_bloc == -1:
                         section_start_bloc   = bloc_idx
                         section['Header']    = s['text']
                         section['StartBloc'] = bloc_idx
                         #print('Section Header', section['Header'] , 'Start Bloc',section['StartBloc'])
                         continue

                      if section_start_bloc > 0 and section_end_bloc == -1:
                         section['EndBloc'] = bloc_idx
                         section['LastSection'] = 0
                         section_end_bloc   = bloc_idx
                         #print('Section Header', section['Header'], 'Start Bloc',section['StartBloc'] , 'End Bloc', section['EndBloc'])
                         section_start_bloc == -1
                         return section
    section['EndBloc'] = bloc_idx
    section['LastSection'] = 1
    section_start_bloc == -1
    return section



def parse_section(pdf_content,section,max_block_id,output_path):
    #print('section',section)
    section_text    = ""
    section["text"] = ""
    images = {}
    for pg, page_content in pdf_content.items():
        for bloc_idx,b in page_content['Blocs'].items():
            #print('Block Index',bloc_idx , 'Start Bloc')
            if bloc_idx > section['StartBloc'] and bloc_idx < section['EndBloc']:
               #print(f'Section - {section["Header"]} - bloc {bloc_idx} - {b}')
               if b['type'] == 0:
                  #print(f'Section - {section["Header"]} - bloc {bloc_idx} - {b}')
                  for line_idx, l in enumerate(sortBlockLines(b["lines"])):
                      for s in sortLineSpans(l["spans"]):
                          #Filter spans of size < 9
                          if int(s['size']) < 9:
                             continue

                          if section_text.endswith(" ") or s["text"].startswith(" "):
                             section_text += s["text"]
                          else:
                             section_text += " " + s["text"]
                      section_text += "\n"

               if b['type'] == 1:
                  #print('Extension'  ,b['ext'])
                  #print('Image Bytes', b['image'])
                  img_stream = BytesIO(b['image'])
                  img = Image.open(img_stream).convert('RGB')
                  output_filepath = os.path.join(output_path,str(uuid.uuid4().hex) + '.png')
                  img.save(output_filepath)
                  img_stream.close()
                  images[bloc_idx] = output_filepath
                  section_text    += ", images {" + str(bloc_idx) + ": '" + output_filepath + "' }"
                  #section["text"][bloc_idx] = output_filepath

    #section["images"] = images
    section["text"]  = section_text
    #print('section')
    #print(section)
    return section
################################################################################################
def parse_pdf_content(input_file:str
                     ,output_path:str
                     ,pages:str):
    """
    Parse PDF content
    """
    pdfIn = fitz.open(input_file)

    output_filename = os.path.join(output_path
                          , os.path.splitext(os.path.basename(input_file))[0]  + ".json")
    output_file = open(output_filename,"w",encoding=ENCODING)
    try:
        pdf_content = {}
        for pg in range(pdfIn.pageCount):
            page_content = {}
            page_content['Page'] = pg

            if pages:
                if (pg + 1) not in pages:
                    continue

            # Load the page
            page = pdfIn.loadPage(pg)
            ###################################################################
            # Extract text block dictionaries of the current page
            page_dict = page.getText("dict")

            # Loop through the arranged page blocks
            bloc_content = {}
            for bloc_idx, b in enumerate(sortPageBlocks(page_dict["blocks"])):
                bloc_index = f'{pg:03d}{bloc_idx:03d}'
                #print(f'Page {pg}, Bloc {bloc_idx}')
                # Text Block
                if b["type"] == 0:
                    bloc_content[int(bloc_index)] = b

                # Image Block (Consider only images of width 580)
                if b["type"] == 1 and b['width'] == 580:
                    bloc_content[int(bloc_index)] = b

                page_content['Blocs'] = bloc_content

            pdf_content[str(pg)] = page_content
        #print('bloc_index',bloc_index)
        #print('pdf_content',pdf_content)

        max_block_id = int(bloc_index)
        print("Max Block ID",max_block_id)

        doc_content = {}
        doc_title_bloc, doc_title = get_document_title(pdf_content)
        print(f'Document title {doc_title} - Bloc {doc_title_bloc}')
        
        doc_content['title'] = doc_title
        doc_sections = {}

        if doc_title_bloc > 0:
           sectionID = 0

           indx = doc_title_bloc
           while True:
                 initial_step = detect_next_starting_step(pdf_content
                                                         ,start_bloc_idx=indx
                                                         ,max_block_id=max_block_id)
                 if initial_step is None:
                     break

                 print('Title=',get_title(pdf_content, initial_step))
                 print('Description=',get_description(pdf_content, initial_step))

                 section = get_section_header(pdf_content
                                            , start_bloc_idx = doc_title_bloc
                                            , max_block_id = max_block_id
                                            , step = initial_step)
                 print("Section=",section)

                 #Get Subsequent steps
                 previous_step = initial_step
                 while True:
                       step = detect_next_step(pdf_content, max_block_id, previous_step)
                       if step is None:
                          break
                       print('Title=', get_title(pdf_content, step))
                       print('Description=', get_description(pdf_content, step))

                       #Get Substeps
                       starting_bloc_idx = int(previous_step["bloc_idx"])
                       while True:
                           substep = get_next_substep(pdf_content
                                                    , max_block_id=int(step["bloc_idx"])
                                                    , step=initial_step
                                                    , starting_bloc_idx=starting_bloc_idx)
                           if substep is None or "bloc_idx" not in substep:
                              break

                           print('Title=', get_title(pdf_content, substep))
                           print('Description=', get_description(pdf_content, substep))
                           starting_bloc_idx = substep["bloc_idx"]

                       previous_step = step

                 indx = int(previous_step['bloc_idx'])

           """ 
           starting_bloc_idx = int(initial_step["bloc_idx"])

           while True:
                 substep = get_next_substep(pdf_content
                                          , max_block_id=int(step["bloc_idx"])
                                          , step=initial_step
                                          , starting_bloc_idx = starting_bloc_idx)
                 if "bloc_idx" in substep:
                    starting_bloc_idx = substep["bloc_idx"]
                    print('starting_bloc_idx',starting_bloc_idx)
                 else:
                    print("break")
                    break
        
           step = detect_next_step(pdf_content, max_block_id, step)
           
           section = get_next_section(pdf_content, start_bloc_idx=(doc_title_bloc+1),max_block_id=max_block_id)
           #print('Section Header', section['Header'], 'Start Bloc', section['StartBloc']
           #      , 'End Bloc',section['EndBloc'] ,'Last Section' , section['LastSection'] )

           section = parse_section(pdf_content,section,max_block_id,output_path)
           sectionID += 1
           doc_sections[sectionID] = section
             
           while True:
                 #print('a' * 20)
                 section = get_next_section(pdf_content,start_bloc_idx=section['EndBloc'],max_block_id=max_block_id)
                 #print('b' * 20)

                 if 'Header' in section:
                    print('Section Header', section['Header'])
                    pass
                 if 'StartBloc' in section:
                    print('Start Bloc', section['StartBloc'])
                    pass
                 if 'EndBloc' in section:
                    print('End Bloc',section['EndBloc'],'max_block_id',max_block_id)
                    pass
                 if 'Last Section' in section:
                    print('Last Section' , section['LastSection'])
                    pass

                 if 'StartBloc' in section:
                    #print('Section Header', section['Header'], 'Start Bloc', section['StartBloc'], 'End Bloc',
                    #    section['EndBloc'] ,'Last Section' , section['LastSection'] )
                    section = parse_section(pdf_content, section,max_block_id,output_path)
                    sectionID +=  1
                    doc_sections[sectionID] = section
                    if section['StartBloc'] == section['EndBloc'] and section['EndBloc'] < max_block_id:
                        #print('max', max_block_id, section['StartBloc'], section['EndBloc'])
                        section['EndBloc'] = section['EndBloc']+1
                 if section['LastSection'] == 1:
                    break

           doc_content['Sections'] = doc_sections
           """
        #print('doc_content')
        #print(doc_content)
        
        #json.dump(doc_content,output_file)

    except Exception as e:
        print("Exception", e)
    else:
        pdfIn.close()
        output_file.close()

if __name__ == '__main__':
    parse_pdf_content(input_file  = ".\\static\\pdfs\\rm.pdf"
                    , output_path = ".\\static\\pdfs\\"
                    , pages = None
                     )
