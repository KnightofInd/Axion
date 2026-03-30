function onHomepage(e) {
  return [buildMainCard_({ tab: 'i_owe' })];
}

function syncNowAction(e) {
  var email = getUserEmail_(e);
  var syncResult = callBackend_('/api/v1/sidebar/sync?email=' + encodeURIComponent(email), 'post', null);
  var card = buildMainCard_({
    tab: 'i_owe',
    flash: syncResult && syncResult.synced ? 'Sync complete.' : 'Sync finished with issues.'
  });
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation().updateCard(card))
    .build();
}

function askAction(e) {
  var email = getUserEmail_(e);
  var question = '';
  if (e && e.formInput && e.formInput.ask_question) {
    question = e.formInput.ask_question;
    if (Array.isArray(question)) {
      question = question[0] || '';
    }
  }
  if (!question) {
    question = 'What should I focus on today?';
  }

  var response = callBackend_(
    '/api/v1/sidebar/ask?email=' + encodeURIComponent(email),
    'post',
    { question: question }
  );

  var card = buildMainCard_({
    tab: 'i_owe',
    askQuestion: question,
    askAnswer: response && response.answer ? response.answer : 'No answer available.'
  });

  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation().updateCard(card))
    .build();
}

function setCommitmentTabAction(e) {
  var tab = 'i_owe';
  if (e && e.parameters && e.parameters.tab) {
    tab = e.parameters.tab;
  }

  var card = buildMainCard_({ tab: tab });
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation().updateCard(card))
    .build();
}

function buildMainCard_(state) {
  var tab = (state && state.tab) || 'i_owe';
  var email = getUserEmail_();
  var overview = callBackend_(
    '/api/v1/sidebar/overview?email=' + encodeURIComponent(email) + '&commitments_tab=' + encodeURIComponent(tab),
    'get',
    null
  );

  if (!overview || overview.error) {
    return buildErrorCard_(overview && overview.error ? overview.error : 'Failed to load AXION sidebar.');
  }

  var sectionHeader = CardService.newCardSection()
    .addWidget(CardService.newKeyValue()
      .setTopLabel('AXION')
      .setContent('Status: ' + (overview.status || 'unknown'))
      .setBottomLabel('User: ' + ((overview.user && overview.user.email) || email)
    ));

  var dashboardUrl = getScriptProperty_('AXION_DASHBOARD_URL', 'http://localhost:3000');
  sectionHeader.addWidget(
    CardService.newTextButton()
      .setText('Open Dashboard')
      .setOpenLink(CardService.newOpenLink().setUrl(dashboardUrl))
  );

  var briefing = (overview.briefing && overview.briefing.text) ? overview.briefing.text : 'Briefing unavailable.';
  var sectionBriefing = CardService.newCardSection()
    .setHeader('Morning Briefing')
    .addWidget(CardService.newTextParagraph().setText(briefing));

  var stats = overview.stats || {};
  var sectionStats = CardService.newCardSection()
    .setHeader('Mission Stats')
    .addWidget(CardService.newTextParagraph().setText(
      'Tasks: ' + (stats.tasks || 0) + ' | Focus: ' + (stats.focus_blocks || 0) + ' | Commitments: ' + (stats.commitments || 0)
    ));

  var sectionTasks = CardService.newCardSection().setHeader('Priority Tasks');
  var tasks = overview.priority_tasks || [];
  if (!tasks.length) {
    sectionTasks.addWidget(CardService.newTextParagraph().setText('All clear. No priority tasks found.'));
  } else {
    tasks.forEach(function(item, idx) {
      if (idx >= 3) return;
      var due = item.due_at ? item.due_at : 'No due date';
      sectionTasks.addWidget(
        CardService.newKeyValue()
          .setTopLabel('P' + (item.priority || 0) + ' | ' + (item.source || 'task'))
          .setContent(item.title || 'Untitled task')
          .setBottomLabel(due)
      );
    });
  }

  var cal = overview.calendar || {};
  var nextSlot = cal.next_free_slot || 'No free slot detected';
  var focusCount = (cal.focus_blocks || []).length;
  var sectionCal = CardService.newCardSection()
    .setHeader('Calendar Intelligence')
    .addWidget(CardService.newTextParagraph().setText('Focus blocks: ' + focusCount + ' | Next free slot: ' + nextSlot));

  var commitments = overview.commitments || {};
  var selected = commitments.selected_items || [];
  var sectionCommitments = CardService.newCardSection().setHeader('Commitments');
  var tabs = CardService.newButtonSet()
    .addButton(
      CardService.newTextButton()
        .setText('I Owe')
        .setOnClickAction(CardService.newAction().setFunctionName('setCommitmentTabAction').setParameters({ tab: 'i_owe' }))
    )
    .addButton(
      CardService.newTextButton()
        .setText('They Owe')
        .setOnClickAction(CardService.newAction().setFunctionName('setCommitmentTabAction').setParameters({ tab: 'they_owe' }))
    );
  sectionCommitments.addWidget(tabs);

  if (!selected.length) {
    sectionCommitments.addWidget(CardService.newTextParagraph().setText('No commitments in this tab.'));
  } else {
    selected.slice(0, 3).forEach(function(item) {
      sectionCommitments.addWidget(
        CardService.newKeyValue()
          .setTopLabel((item.status || 'open').toUpperCase())
          .setContent((item.text || '').substring(0, 140))
          .setBottomLabel(item.due_at || 'No due date')
      );
    });
  }

  var askQuestion = (state && state.askQuestion) || '';
  var askAnswer = (state && state.askAnswer) || '';
  var sectionAsk = CardService.newCardSection().setHeader('Ask AXION');
  sectionAsk.addWidget(
    CardService.newTextInput()
      .setFieldName('ask_question')
      .setTitle('Question')
      .setHint('What did I promise this week?')
      .setValue(askQuestion)
  );
  sectionAsk.addWidget(
    CardService.newTextButton()
      .setText('Ask')
      .setOnClickAction(CardService.newAction().setFunctionName('askAction'))
  );
  if (askAnswer) {
    sectionAsk.addWidget(CardService.newTextParagraph().setText(askAnswer));
  }

  var sectionSync = CardService.newCardSection();
  sectionSync.addWidget(
    CardService.newTextButton()
      .setText('Sync Now')
      .setOnClickAction(CardService.newAction().setFunctionName('syncNowAction'))
  );
  if (state && state.flash) {
    sectionSync.addWidget(CardService.newTextParagraph().setText(state.flash));
  }

  var card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('AXION'))
    .addSection(sectionHeader)
    .addSection(sectionBriefing)
    .addSection(sectionStats)
    .addSection(sectionTasks)
    .addSection(sectionCal)
    .addSection(sectionCommitments)
    .addSection(sectionAsk)
    .addSection(sectionSync)
    .build();

  return card;
}

function buildErrorCard_(message) {
  return CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader().setTitle('AXION'))
    .addSection(
      CardService.newCardSection()
        .addWidget(CardService.newTextParagraph().setText('Sidebar error: ' + message))
    )
    .build();
}

function callBackend_(path, method, body) {
  var baseUrl = getScriptProperty_('AXION_BACKEND_BASE_URL', 'http://localhost:8000');
  var apiKey = getScriptProperty_('AXION_INTERNAL_API_KEY', '');

  var options = {
    method: (method || 'get').toUpperCase(),
    muteHttpExceptions: true,
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (apiKey) {
    options.headers['x-axion-api-key'] = apiKey;
  }

  if (body) {
    options.payload = JSON.stringify(body);
  }

  var url = baseUrl + path;
  var response = UrlFetchApp.fetch(url, options);
  var status = response.getResponseCode();
  var text = response.getContentText();

  if (status >= 200 && status < 300) {
    if (!text) return {};
    return JSON.parse(text);
  }

  return {
    error: 'HTTP ' + status + ': ' + text
  };
}

function getUserEmail_(e) {
  var fallback = getScriptProperty_('AXION_DEFAULT_EMAIL', '');
  var active = Session.getActiveUser().getEmail();
  if (active) {
    return active;
  }
  if (e && e.user && e.user.email) {
    return e.user.email;
  }
  return fallback;
}

function getScriptProperty_(key, defaultValue) {
  var value = PropertiesService.getScriptProperties().getProperty(key);
  if (!value) return defaultValue;
  return value;
}
