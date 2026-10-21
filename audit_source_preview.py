"""NAV-012 mouse interaction and non-mutating rendering audit. Flow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import subprocess
import sys
import uuid
from unittest.mock import patch
from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from audit_source_selection import fixture as source_fixture
from audit_visibility_presets import wait
from attack_catalog import external_id
from attack_matrix import MATRIX_ID, MATRIX_SLUG, MATRIX_STYLE
from custom_sources import load_custom
from main import MainWindow, configure_application, ROLE_CONTEXT
from matrix_exports import export_matrix
from navigator_integration import document_layer
from studio_files import save_studio
from ttp_documents import TTPDocument
from ttp_selection import selected_cells
from source_preview import PREVIEW_COLOR, SourceResultHover

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
OUT=ROOT/'artifacts'/'source-preview'
CHECKS=[]


def log(text,current=0,total=0): print(text+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,text):
    if not value: raise AssertionError(text)
    CHECKS.append(text)


def fixture():
    payload=source_fixture()
    child=next(o for o in payload['objects'] if o.get('type')=='attack-pattern' and external_id(o)=='T1000.001')
    key='intrusion-set--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'hover child only'))
    payload['objects'].extend([
        {'type':'intrusion-set','id':key,'name':'Hover child only','x_mitre_domains':['enterprise-attack'],
         'external_references':[{'source_name':'mitre-attack','external_id':'G2000'}]},
        {'type':'relationship','id':'relationship--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'hover child edge')),
         'relationship_type':'uses','source_ref':key,'target_ref':child['id']}])
    return payload


def move(view,index):
    check(index.isValid(),'hover result index exists')
    view.scrollTo(index)
    QtWidgets.QApplication.processEvents()
    point=view.visualRect(index).center()
    check(view.viewport().rect().contains(point),'hover result lies inside viewport')
    QtTest.QTest.mouseMove(view.viewport(),point+QtCore.QPoint(1,0))
    QtTest.QTest.mouseMove(view.viewport(),point)
    QtTest.QTest.qWait(20)


def popup_index(matrix,key):
    view=matrix.source_picker.view()
    return next(view.model().index(row,0) for row in range(view.model().rowCount())
                if view.model().index(row,0).data(QtCore.Qt.ItemDataRole.UserRole)==key)


def surface(matrix,key,slug='execution'):
    column=next(col for col in matrix.columns if col['slug']==slug)
    if 'tree' in column: return column['tree'].viewport()
    return next(family['root'] for family in column['view'].families if family['root'].key==key)


def snapshot(w):
    m=w.matrix_view
    styles={}
    for column in m.columns:
        if 'tree' in column:
            tree=column['tree']
            for i in range(tree.topLevelItemCount()):
                item=tree.topLevelItem(i)
                for row in [item,*[item.child(j) for j in range(item.childCount())]]:
                    styles[row.data(0,MATRIX_ID),column['slug']]=deepcopy(row.data(0,MATRIX_STYLE))
        else:
            for family in column['view'].families:
                for cell in [family['root'],*family['children']]: styles[cell.key,cell.slug]=deepcopy(cell.projection)
    return ([doc.content_token() for doc in w.documents],[doc.dirty for doc in w.documents],
            [selected_cells(doc) for doc in w.documents],deepcopy(document_layer(w.current_document)),
            m.expansion_snapshot(),styles,m.search.text(),m.source_picker.currentText(),w.search.text())


def leave(view):
    QtWidgets.QApplication.sendEvent(view.viewport(),QtCore.QEvent(QtCore.QEvent.Type.Leave))
    QtWidgets.QApplication.processEvents()


def lifecycle():
    log('Input files: None; output files: None (isolated Qt destruction regression)')
    log('[Hover Lifecycle 1/2] Installing a source watcher on a native combo view',0,2)
    app=QtWidgets.QApplication([])
    combo=QtWidgets.QComboBox()
    combo.setEditable(True);combo.addItem('one')
    watch=SourceResultHover(combo.view(),lambda index,owner:None,lambda owner:None)
    combo.close();app.processEvents()
    # Retain the native target/filter together until interpreter cleanup, as
    # Qt signal references do in the full window. Local-only teardown is earlier.
    globals()['_lifecycle_retained']=(app,combo,watch)
    log('[Hover Lifecycle 2/2] Returning for native interpreter/window teardown',2,2)


def main():
    log('Input directory: '+str(DATA.resolve()))
    log('Output directory: '+str(OUT.resolve()))
    for name in ('fixture.json','settings.ini','state.studio.json','during-hover.svg','audit.json',
                 'flat-hover.png','flat-cleared.png','side-hover.png','side-cleared.png',
                 'mini-hover.png','mini-cleared.png','sidebar-hover.png','overlay-hover.png'):
        log('Output file: '+str((OUT/name).resolve()))
    log('[Hover Audit 1/7] Preparing isolated source mappings',0,7)
    log('Input file: '+str(Path(__file__).resolve())+' (--lifecycle-only subprocess)')
    log('Output files: None (captured lifecycle diagnostics in memory)')
    result=subprocess.run([sys.executable,'-X','faulthandler','-B',str(Path(__file__).resolve()),'--lifecycle-only'],
                          cwd=ROOT,capture_output=True,text=True,timeout=30)
    log(result.stdout.strip())
    if result.stderr: log(result.stderr.strip())
    check(result.returncode==0,'isolated native view destruction exits normally without viewport access during teardown')
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in (DATA/'latest.json',DATA/'active.json') if p.exists()}
    path=OUT/'fixture.json';path.write_text(json.dumps(fixture()),encoding='utf-8')
    catalog=load_custom(DATA,str(path),'19.2',log)['catalog']
    store=catalog.objects_by_domain[catalog.domain]
    tags={obj.get('x_fixture'):key for key,obj in store.items() if obj.get('x_fixture')}
    ids={external_id(obj):key for key,obj in store.items() if external_id(obj)}
    root,child,beta=ids['T1000'],ids['T1000.001'],ids['T1001']
    group,child_group=ids['G1000'],ids['G2000']
    doc=TTPDocument('Hover example',catalog,selected={root},navigator_layer={'name':'Hover example','domain':catalog.domain,
        'techniques':[{'techniqueID':'T1000','color':'#cc5522','score':8,'comment':'Keep parent note',
                       'metadata':[{'name':'Owner','value':'Blue'}],'links':[{'label':'Reference','url':'https://example.org/'}]},
                      {'techniqueID':'T1000.001','color':'#11aa33','enabled':False,'score':0,'comment':'Disabled child'},
                      {'techniqueID':'T1001','color':'#334455','score':4}]})
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    w=MainWindow(DATA,DATA/'latest.json',settings_path=OUT/'settings.ini');w.resize(1900,1120);w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        w.install_imported_document(doc);wait(lambda:w.loaded_ok)
        w.open_matrix();m=w.matrix_view;wait(lambda:not m.building)
        log('[Hover Audit 2/7] Actual dropdown mouse moves and pixel restoration in every layout',1,7)
        for mode in ('Flat','Side','Mini'):
            m.view_layout.setCurrentText(mode);wait(lambda:not m.building)
            m.collapse_button.click()
            doc.selection_preferences.update(with_family=True,visible_only=True,across_tactics=False)
            save_studio(doc,OUT/'state.studio.json',log)
            m.source_kind.setCurrentText('Group');m.source_picker.setEditText('');m.source_picker.showPopup()
            QtWidgets.QApplication.processEvents();m.clear_source_preview()
            before=snapshot(w);base=surface(m,root).grab().toImage()
            move(m.source_picker.view(),popup_index(m,group))
            check(m.source_preview_cells=={(root,'execution'),(root,'initial-access')},mode+' preview ignores family selection preference and covers exact mapped tactics')
            check(snapshot(w)==before,mode+' hover preserves clean/dirty state, selection, annotations, styles, expansion and queries')
            check(surface(m,root).grab().toImage()!=base,mode+' preview actually changes painted pixels')
            check(m.grab().save(str(OUT/(mode.lower()+'-hover.png'))),mode+' hover screenshot')
            leave(m.source_picker.view())
            check(not m.source_preview_cells and m.source_preview_context is None,mode+' leave clears temporary state')
            check(surface(m,root).grab().toImage()==base,mode+' leave restores exact base pixels')
            check(snapshot(w)==before,mode+' restored document and projection unchanged')
            check(m.grab().save(str(OUT/(mode.lower()+'-cleared.png'))),mode+' cleared screenshot')
            move(m.source_picker.view(),popup_index(m,child_group))
            check(m.source_preview_cells=={(child,'execution')},mode+' collapsed source maps only the actual child')
            check(m.source_preview_kind(root,'execution',[child],False)=='family' and not m.source_preview_kind(root,'initial-access',[child],False),mode+' collapsed parent hint is tactic-specific')
            check(m.expansion_snapshot()==before[4],mode+' child preview does not expand families')
            check(surface(m,root).grab().toImage()!=base,mode+' collapsed-child hint is visibly painted')
            m.source_picker.hidePopup();QtWidgets.QApplication.processEvents()
            check(not m.source_preview_cells,mode+' closing dropdown clears preview')
            check(snapshot(w)==before,mode+' popup close preserves document')
        log('[Hover Audit 3/7] Completion popup, rapid movement and owner isolation',2,7)
        m.view_layout.setCurrentText('Flat');wait(lambda:not m.building)
        m.source_kind.setCurrentText('Group');m.source_picker.setEditText('Hover')
        m.source_completer.setCompletionPrefix('Hover');m.source_completer.complete();QtWidgets.QApplication.processEvents()
        popup=m.source_completer.popup();index=popup.model().index(0,0)
        check(index.data(QtCore.Qt.ItemDataRole.UserRole)==child_group,'completion model preserves source ID role')
        move(popup,index)
        check(m.source_preview_cells=={(child,'execution')},'actual completion hover resolves exact source')
        m.source_hover_filters[0].clear()
        check(m.source_preview_cells=={(child,'execution')},'old dropdown leave cannot clear completion-owned preview')
        QtTest.QTest.keyClick(popup,QtCore.Qt.Key.Key_Escape);QtWidgets.QApplication.processEvents()
        check(not m.source_preview_cells,'Escape closes completion and clears preview')
        m.source_picker.setEditText('');m.source_picker.showPopup();QtWidgets.QApplication.processEvents()
        before=snapshot(w)
        for key in (group,child_group,group,child_group): move(m.source_picker.view(),popup_index(m,key))
        check(m.source_preview_cells=={(child,'execution')} and snapshot(w)==before,'rapid source changes retain only newest mapping without document edits')
        viewport=m.source_picker.view().viewport();point=viewport.rect().center()
        wheel=QtGui.QWheelEvent(QtCore.QPointF(point),QtCore.QPointF(viewport.mapToGlobal(point)),QtCore.QPoint(),QtCore.QPoint(0,-240),
            QtCore.Qt.MouseButton.NoButton,QtCore.Qt.KeyboardModifier.NoModifier,QtCore.Qt.ScrollPhase.ScrollUpdate,False)
        app.sendEvent(viewport,wheel);app.processEvents()
        check(not m.source_preview_cells,'actual wheel event clears stale hovered-row preview')
        m.source_picker.hidePopup();m.source_kind.setCurrentText('Data Component');m.source_picker.showPopup();QtWidgets.QApplication.processEvents()
        move(m.source_picker.view(),popup_index(m,tags['component']))
        check(m.source_preview_cells=={(root,'execution'),(root,'initial-access'),(child,'execution'),(beta,'execution')},'component paths preview full deduplicated mapping')
        move(m.source_picker.view(),popup_index(m,tags['same-label-component']))
        check(not m.source_preview_cells,'same-label empty source clears prior colors instead of using its neighbor')
        m.source_picker.hidePopup()
        m.show_colors.setChecked(False);m.source_kind.setCurrentText('Group');m.source_picker.setEditText('')
        m.source_picker.showPopup();QtWidgets.QApplication.processEvents();m.clear_source_preview()
        base=surface(m,root).grab().toImage();before=snapshot(w)
        move(m.source_picker.view(),popup_index(m,group))
        check(surface(m,root).grab().toImage()!=base,'preview still paints when layer annotation colors are hidden')
        leave(m.source_picker.view())
        check(surface(m,root).grab().toImage()==base and snapshot(w)==before,'hidden-color preview restores pixels and document exactly')
        m.source_picker.hidePopup();m.show_colors.setChecked(True)
        log('[Hover Audit 4/7] Sidebar result hover and explicit matrix entry',3,7)
        w.switch_category('Groups');w.search.setText('Hover child');w.apply_search()
        before_token=doc.content_token();w.source_matrix_button.click();wait(lambda:not m.building)
        check(w.active_category=='Groups' and w.search.text()=='Hover child' and m.isVisible(),'matrix preview entry retains source category and query')
        check(doc.content_token()==before_token,'opening sidebar matrix preview does not edit document')
        item=next(item for item in w.library_items['Groups'] if item.data(ROLE_CONTEXT)[2]==child_group)
        index=w.library_proxy.mapFromSource(item.index());w.library_tree.expandAll();QtWidgets.QApplication.processEvents()
        before=snapshot(w);move(w.library_tree,index)
        check(m.source_preview_cells=={(child,'execution')} and snapshot(w)==before,'actual sidebar hover previews source without selecting or opening details')
        check(w.grab().save(str(OUT/'sidebar-hover.png')),'sidebar hover screenshot')
        leave(w.library_tree);check(not m.source_preview_cells,'sidebar leave clears preview')
        w.search.clear();w.apply_search();w.library_tree.expandAll()
        foreign=next(item for item in w.library_items['Groups'] if item.data(ROLE_CONTEXT)[0]=='ics-attack')
        move(w.library_tree,w.library_proxy.mapFromSource(foreign.index()))
        check(not m.source_preview_cells,'other-domain library result cannot highlight active document')
        token=doc.content_token()
        check(w.change_language('zh_TW'),'Chinese interface switch succeeds')
        app.processEvents()
        check(w.source_matrix_button.text()=='顯示矩陣預覽' and doc.content_token()==token,'new preview control translates without editing document')
        w.change_language('en');app.processEvents()
        log('[Hover Audit 5/7] Filters, hidden disabled children and lifecycle cleanup',4,7)
        w.open_matrix();wait(lambda:not m.building)
        m.source_kind.setCurrentText('Group');m.source_picker.showPopup();QtWidgets.QApplication.processEvents()
        move(m.source_picker.view(),popup_index(m,group));m.search.setText('Beta');QtWidgets.QApplication.processEvents()
        check(not m.source_preview_cells,'matrix search change clears old preview')
        m.search.clear();QtWidgets.QApplication.processEvents()
        m.source_picker.showPopup();move(m.source_picker.view(),popup_index(m,group))
        m.source_picker.setEditText('not a result');check(not m.source_preview_cells,'source query change clears preview immediately')
        m.source_picker.hidePopup();m.source_picker.setEditText('');m.source_kind.setCurrentText('Group')
        doc.navigator_layer['hideDisabled']=True;w.refresh_layer_appearance();m.collapse_button.click()
        m.source_picker.showPopup();QtWidgets.QApplication.processEvents();m.clear_source_preview()
        base=surface(m,root).grab().toImage();move(m.source_picker.view(),popup_index(m,child_group))
        check(surface(m,root).grab().toImage()==base,'hidden disabled child does not paint misleading parent hint')
        m.source_picker.hidePopup();doc.navigator_layer['hideDisabled']=False;w.refresh_layer_appearance()
        m.source_picker.showPopup();move(m.source_picker.view(),popup_index(m,group))
        owner=m.source_hover_filters[0];check(not m.preview_source(replace(catalog,dataset_id='f'*64),group,owner) and not m.source_preview_cells,'stale dataset preview rejected and cleared')
        m.source_picker.showPopup();move(m.source_picker.view(),popup_index(m,group))
        m.platform.setCurrentText('Linux');wait(lambda:not m.building)
        check(not m.source_preview_cells and not m.source_picker.view().isVisible(),'platform rebuild closes source popup and clears preview')
        m.platform.setCurrentText('All Platforms');wait(lambda:not m.building)
        log('[Hover Audit 6/7] Document switching, overlay and export isolation',5,7)
        m.source_kind.setCurrentText('Group');m.source_picker.showPopup();move(m.source_picker.view(),popup_index(m,group))
        other=TTPDocument('Overlay example',catalog,navigator_layer={'name':'Overlay example','domain':catalog.domain,
            'techniques':[{'techniqueID':'T1000','color':'#2255cc'}]})
        w.install_imported_document(other);wait(lambda:w.loaded_ok and not m.building)
        check(not m.source_preview_cells and not m.source_picker.view().isVisible(),'same-catalog document switch clears and dismisses old popup')
        w.select_navigator_layer(doc.document_id);wait(lambda:w.loaded_ok and not m.building)
        w.open_matrix();m.show_all_layers.setChecked(True);QtWidgets.QApplication.processEvents()
        m.source_kind.setCurrentText('Group');m.source_picker.showPopup();QtWidgets.QApplication.processEvents();m.clear_source_preview()
        before=snapshot(w);color=deepcopy(m.appearance.cell('T1000','execution'));base=surface(m,root).grab().toImage()
        move(m.source_picker.view(),popup_index(m,group))
        check(surface(m,root).grab().toImage()!=base,'overlay preview draws over blended cells')
        check(m.appearance.cell('T1000','execution')==color and snapshot(w)==before,'overlay colors, annotations and source layers remain unchanged')
        check(m.grab().save(str(OUT/'overlay-hover.png')),'overlay hover screenshot')
        export_matrix(doc,OUT/'during-hover.svg','svg',log)
        check(PREVIEW_COLOR not in (OUT/'during-hover.svg').read_text(encoding='utf-8').lower(),'SVG excludes transient preview strokes')
        check(document_layer(doc)==before[3],'Navigator/Studio document serialization contains no preview state')
        leave(m.source_picker.view());check(surface(m,root).grab().toImage()==base,'overlay leave restores exact pixels without residual color')
        m.source_picker.hidePopup()
        m.source_picker.showPopup();move(m.source_picker.view(),popup_index(m,group))
        with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
        app.processEvents()
        check(not m.source_preview_cells and not m.source_preview_context,'closing application while hovering clears temporary state')
        log('[Hover Audit 7/7] Pointer preservation and verified report',6,7)
        check(all(p.read_bytes()==value for p,value in pointers.items()),'official data pointers unchanged')
        (OUT/'audit.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS},indent=2),encoding='utf-8')
        log(f'[Hover Audit] PASS: {len(CHECKS)} checks',7,7)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
        QtWidgets.QApplication.processEvents()


if __name__=='__main__':
    if '--lifecycle-only' in sys.argv: lifecycle()
    else: main()
